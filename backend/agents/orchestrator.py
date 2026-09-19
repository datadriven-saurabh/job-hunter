import json
import hashlib
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from backend.agents.scout_agent import score, job_id
from backend.agents.classifier import classify
from backend.database import execute, query
from backend import database as db
from backend.services.job_intelligence import enrich
from backend.state import queue_reservation
from backend.services.job_dedup import fingerprint

class DiscoveryState(TypedDict):
    jobs: list
    profile: dict
    criteria: dict
    matched: list
    count: int
    skip_seen: bool
    skipped: int
    seen: list

def scout(state):
    matched=[];seen=[];skipped=0
    criteria_hash=hashlib.sha256(json.dumps(state['criteria'],sort_keys=True).encode()).hexdigest()
    history={r['job_key']:r for r in query('SELECT * FROM discovery_seen')}
    known={job_id(r['job_url']) for r in query('SELECT job_url FROM application_records')}
    known.update(r['job_id'] for r in query('SELECT job_id FROM application_records'))
    for job in state['jobs']:
        key=job_id(job['job_url']);content_hash=fingerprint(job);old=history.get(key)
        if state.get('skip_seen') and (key in known or old and old['content_hash']==content_hash and old['criteria_hash']==criteria_hash):
            skipped+=1;continue
        seen.append({'key':key,'content':content_hash,'criteria':criteria_hash})
        history[key]={'content_hash':content_hash,'criteria_hash':criteria_hash}
        value=score(job,state['profile'],state['criteria'])
        if value is not None: matched.append(dict(job, match_score=value, job_id=key))
    return {'matched':matched,'skipped':skipped,'seen':seen}

def triage(state):
    return {'matched':[dict(j,classification=classify(j)) for j in state['matched']]}

def persist(state):
    with queue_reservation:
        return _persist(state)

def _persist(state):
    from backend.services.job_dedup import fingerprint,quality
    existing=[dict(json.loads(r['payload']),job_id=r['job_id']) for r in query('SELECT job_id,payload FROM job_details')]
    identities={r['job_id']:r for r in query('SELECT job_id,company_name,job_title,job_url,status FROM application_records')}
    for entry in existing:entry.update({k:v for k,v in identities.get(entry['job_id'],{}).items() if k!='status'})
    protected={r['job_id'] for r in query('SELECT DISTINCT job_id FROM studio_kits WHERE job_id IS NOT NULL')}
    protected.update(id for id,record in identities.items() if record.get('status') not in {'DISCOVERED','MATCHED'})
    saved_ids=set()
    for j in state['matched']:
        if j['job_id'] in protected:continue
        old=query('SELECT payload FROM job_details WHERE job_id=:id',{'id':j['job_id']})
        previous=json.loads(old[0]['payload']) if old else {}
        j=enrich(j,previous)
        if previous.get('alternative_sources'):j['alternative_sources']=previous['alternative_sources']
        duplicate=next((other for other in existing if other['job_id']!=j['job_id'] and len(j.get('description',''))>100 and fingerprint(other)==fingerprint(j)),None)
        if duplicate:
            alternatives=list({(a['source'],a['url']):a for a in duplicate.get('alternative_sources',[])+[{'source':duplicate.get('source','Manual import'),'url':duplicate['job_url']},{'source':j.get('source','Manual import'),'url':j['job_url']} ]}.values())
            preferred=j if quality(j)>quality(duplicate) else duplicate
            j=dict(preferred,job_id=duplicate['job_id'],alternative_sources=alternatives,first_seen_at=duplicate.get('first_seen_at') or j['first_seen_at'],last_seen_at=j['last_seen_at'])
            if j['job_id'] in protected:continue
            execute('UPDATE application_records SET job_url=:url WHERE job_id=:id',{'url':j['job_url'],'id':j['job_id']})
        if j['job_id'] in protected:continue
        if j['job_id'] not in identities:
            saved_ids.add(j['job_id'])
            identities[j['job_id']]=j
        existing.append(j)
        execute('INSERT OR IGNORE INTO application_records (job_id,user_id,company_name,job_title,job_url,match_score,classification,status) VALUES (:job_id,:user_id,:company_name,:job_title,:job_url,:match_score,:classification,\'MATCHED\')',dict(j,user_id=state['profile']['user_id']))
        execute('UPDATE application_records SET match_score=:score WHERE job_id=:id',{'id':j['job_id'],'score':j['match_score']})
        execute('INSERT INTO job_details(job_id,payload) VALUES (:id,:payload) ON CONFLICT(job_id) DO UPDATE SET payload=excluded.payload',{'id':j['job_id'],'payload':json.dumps({k:v for k,v in j.items() if k not in ['job_id','match_score','classification','company_name','job_title','job_url']})})
    for row in state.get('seen',[]):
        if db.HOSTED:
            execute('INSERT INTO discovery_seen(user_id,job_key,content_hash,criteria_hash) VALUES (:user_id,:key,:content,:criteria) ON CONFLICT(user_id,job_key) DO UPDATE SET content_hash=excluded.content_hash,criteria_hash=excluded.criteria_hash,seen_at=CURRENT_TIMESTAMP',dict(row,user_id=state['profile']['user_id']))
        else:
            execute('INSERT INTO discovery_seen(job_key,content_hash,criteria_hash) VALUES (:key,:content,:criteria) ON CONFLICT(job_key) DO UPDATE SET content_hash=excluded.content_hash,criteria_hash=excluded.criteria_hash,seen_at=CURRENT_TIMESTAMP',row)
    return {'count':len(saved_ids),'skipped':state.get('skipped',0)+len(state['matched'])-len(saved_ids)}

builder=StateGraph(DiscoveryState)
for name,node in [('scout',scout),('classifier',triage),('persist',persist)]: builder.add_node(name,node)
builder.add_edge(START,'scout');builder.add_edge('scout','classifier');builder.add_edge('classifier','persist');builder.add_edge('persist',END)
discovery_graph=builder.compile()
