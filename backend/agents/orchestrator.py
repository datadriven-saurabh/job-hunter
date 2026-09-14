import json
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from backend.agents.scout_agent import score, job_id
from backend.agents.classifier import classify
from backend.database import execute

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
    for j in state['matched']:
        execute('INSERT OR IGNORE INTO application_records (job_id,user_id,company_name,job_title,job_url,match_score,classification,status) VALUES (:job_id,:user_id,:company_name,:job_title,:job_url,:match_score,:classification,\'MATCHED\')',dict(j,user_id=state['profile']['user_id']))
        execute('UPDATE application_records SET match_score=:score WHERE job_id=:id',{'id':j['job_id'],'score':j['match_score']})
        execute('INSERT OR REPLACE INTO job_details VALUES (:id,:payload)',{'id':j['job_id'],'payload':json.dumps({k:v for k,v in j.items() if k not in ['job_id','match_score','classification','company_name','job_title','job_url']})})
    return {'count':len(state['matched'])}

builder=StateGraph(DiscoveryState)
for name,node in [('scout',scout),('classifier',triage),('persist',persist)]: builder.add_node(name,node)
builder.add_edge(START,'scout');builder.add_edge('scout','classifier');builder.add_edge('classifier','persist');builder.add_edge('persist',END)
discovery_graph=builder.compile()
