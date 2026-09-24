"""Per-user search progress and source timing, persisted through the database."""
import json
import time
import uuid
from threading import Lock
from contextvars import copy_context
from concurrent.futures import ThreadPoolExecutor
from fastapi import HTTPException
from backend import database as db

_lock=Lock()
_pool=ThreadPoolExecutor(max_workers=2, thread_name_prefix='search-run')
_active={}
MAX_SOURCES=3

def read(key):
    rows=db.query('SELECT payload FROM source_cache WHERE cache_key=:key',{'key':key})
    return json.loads(rows[0]['payload']) if rows else None

def write(key,value):
    db.execute('INSERT INTO source_cache(cache_key,fetched_at,payload) VALUES (:key,:time,:payload) ON CONFLICT(cache_key) DO UPDATE SET fetched_at=excluded.fetched_at,payload=excluded.payload',{'key':key,'time':time.time(),'payload':json.dumps(value)})

def metric_key(source):return 'search-metric:'+db.current_user()+':'+source

def catalog(rows):
    result=[]
    for row in rows:
        m=read(metric_key(row['id'])) or {}
        remaining=max(0,int(m.get('last_success',0)+600-time.time()))
        result.append({**row,'cooldown_seconds':remaining,'estimated_seconds':round(m.get('estimate',20),1), 'timing_samples':m.get('samples',0)})
    return sorted(result,key=lambda row:(not row['available'],row['estimated_seconds']))

def status(run_id):
    value=read('search-run:'+db.current_user()+':'+run_id)
    if not value:raise HTTPException(404,'Search not found')
    if value['state'] in {'queued','running'} and time.time()-value['updated_at']>300:
        value.update(state='interrupted',message='Search was interrupted. Saved results are retained; refresh opportunities before retrying.')
    return value

def start(body,search,rows):
    user=db.current_user();providers=list(dict.fromkeys(body.sources or [body.provider]))
    if not 1<=len(providers)<=MAX_SOURCES:raise HTTPException(400,'Select between 1 and 3 job boards.')
    with _lock:
        if user in _active:return {'run_id':_active[user],'state':'running'}
        choices={r['id']:r for r in catalog(rows)}
        for source in providers:
            r=choices.get(source)
            if not r or not r['available'] or r['kind']=='company-board':raise HTTPException(400,'This source is unavailable for automatic discovery.')
            if r['cooldown_seconds']:raise HTTPException(429,f"{r['name']} is cooling down. Retry in {r['cooldown_seconds']} seconds.")
        if sum(choices[s]['estimated_seconds'] for s in providers)>60:raise HTTPException(400,'Estimated search time exceeds one minute. Select fewer or faster boards.')
        if len(_active)>=2:raise HTTPException(429,'Search capacity is busy. Please try again shortly.')
        run_id=uuid.uuid4().hex;key='search-run:'+user+':'+run_id
        value={'run_id':run_id,'state':'queued','sources':[],'count':0,'completed':0,'total':len(providers),'updated_at':time.time(),'message':'Search queued'}
        write(key,value);_active[user]=run_id
        context=copy_context()
        def work():
            try:
                for source in providers:
                    value.update(state='running',message='Fetching and matching '+choices[source]['name'],updated_at=time.time());write(key,value)
                    started=time.monotonic()
                    result=search(body.model_copy(update={'sources':[source]}))
                    elapsed=time.monotonic()-started
                    reports=result.get('sources',[])
                    metric=read(metric_key(source)) or {}
                    metric.update(estimate=max(elapsed,metric.get('estimate',elapsed)*0.7+elapsed*0.3),samples=metric.get('samples',0)+1)
                    if any(r['status']=='success' for r in reports):metric['last_success']=time.time()
                    write(metric_key(source),metric)
                    value['sources'].extend(reports);value['count']+=result.get('count',0);value['completed']+=1;value['updated_at']=time.time();write(key,value)
                value.update(state='complete',message=f"Search finished: {value['count']} new opportunities.")
            except Exception:
                value.update(state='failed',message='Search could not finish. Completed results are saved; refresh opportunities before retrying.')
            finally:
                try:value['updated_at']=time.time();write(key,value)
                finally:
                    with _lock:_active.pop(user,None)
        _pool.submit(context.run,work)
        return {'run_id':run_id,'state':'queued'}
