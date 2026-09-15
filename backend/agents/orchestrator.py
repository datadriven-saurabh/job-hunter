import json
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from backend.agents.scout_agent import score, job_id
from backend.agents.classifier import classify
from backend.database import execute, query
from backend.services.job_intelligence import enrich

class DiscoveryState(TypedDict):
    jobs: list
    profile: dict
    criteria: dict
    matched: list
    count: int

def scout(state):
    matched=[]
    for job in state['jobs']:
        value=score(job,state['profile'],state['criteria'])
        if value is not None: matched.append(dict(job, match_score=value, job_id=job_id(job['job_url'])))
    return {'matched':matched}

def triage(state):
    return {'matched':[dict(j,classification=classify(j)) for j in state['matched']]}

def persist(state):
    from backend.services.job_dedup import fingerprint,quality
    existing=[dict(json.loads(r['payload']),job_id=r['job_id']) for r in query('SELECT job_id,payload FROM job_details')]
    identities={r['job_id']:r for r in query('SELECT job_id,company_name,job_title,job_url FROM application_records')}
    for entry in existing:entry.update(identities.get(entry['job_id'],{}))
    saved_ids=set()
    for j in state['matched']:
        old=query('SELECT payload FROM job_details WHERE job_id=:id',{'id':j['job_id']})
        previous=json.loads(old[0]['payload']) if old else {}
        j=enrich(j,previous)
        if previous.get('alternative_sources'):j['alternative_sources']=previous['alternative_sources']
        duplicate=next((other for other in existing if other['job_id']!=j['job_id'] and len(j.get('description',''))>100 and fingerprint(other)==fingerprint(j)),None)
        if duplicate:
            alternatives=list({(a['source'],a['url']):a for a in duplicate.get('alternative_sources',[])+[{'source':duplicate.get('source','Manual import'),'url':duplicate['job_url']},{'source':j.get('source','Manual import'),'url':j['job_url']} ]}.values())
            preferred=j if quality(j)>quality(duplicate) else duplicate
            j=dict(preferred,job_id=duplicate['job_id'],alternative_sources=alternatives,first_seen_at=duplicate.get('first_seen_at') or j['first_seen_at'],last_seen_at=j['last_seen_at'])
            execute('UPDATE application_records SET job_url=:url WHERE job_id=:id',{'url':j['job_url'],'id':j['job_id']})
        saved_ids.add(j['job_id'])
        existing.append(j)
        execute('INSERT OR IGNORE INTO application_records (job_id,user_id,company_name,job_title,job_url,match_score,classification,status) VALUES (:job_id,:user_id,:company_name,:job_title,:job_url,:match_score,:classification,\'MATCHED\')',dict(j,user_id=state['profile']['user_id']))
        execute('UPDATE application_records SET match_score=:score WHERE job_id=:id',{'id':j['job_id'],'score':j['match_score']})
        execute('INSERT OR REPLACE INTO job_details VALUES (:id,:payload)',{'id':j['job_id'],'payload':json.dumps({k:v for k,v in j.items() if k not in ['job_id','match_score','classification','company_name','job_title','job_url']})})
    return {'count':len(saved_ids)}

builder=StateGraph(DiscoveryState)
for name,node in [('scout',scout),('classifier',triage),('persist',persist)]: builder.add_node(name,node)
builder.add_edge(START,'scout');builder.add_edge('scout','classifier');builder.add_edge('classifier','persist');builder.add_edge('persist',END)
discovery_graph=builder.compile()
