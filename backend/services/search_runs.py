"""Per-user search progress and source timing, persisted through the database."""
import json
import time
import uuid
from threading import Lock
from contextvars import copy_context
from concurrent.futures import ThreadPoolExecutor
from fastapi import HTTPException
from backend import database as db
from backend.services.discovery_fetch import SOURCE_TIMEOUT_SECONDS

_lock=Lock()
_pool=ThreadPoolExecutor(max_workers=2, thread_name_prefix='search-run')
_active={}
MAX_SOURCES=3
NO_OUTPUT_PAUSE_SECONDS=3600

def read(key):
    rows=db.query('SELECT payload FROM source_cache WHERE cache_key=:key',{'key':key})
    return json.loads(rows[0]['payload']) if rows else None

def write(key,value):
    db.execute('INSERT INTO source_cache(cache_key,fetched_at,payload) VALUES (:key,:time,:payload) ON CONFLICT(cache_key) DO UPDATE SET fetched_at=excluded.fetched_at,payload=excluded.payload',{'key':key,'time':time.time(),'payload':json.dumps(value)})

def metric_key(source):return 'search-metric:'+db.current_user()+':'+source

def catalog(rows):
    prefix='search-metric:'+db.current_user()+':'
    metrics={r['cache_key']:json.loads(r['payload']) for r in db.query("SELECT cache_key,payload FROM source_cache WHERE cache_key LIKE :prefix",{'prefix':prefix+'%'})}
    result=[]
    for row in rows:
        m=metrics.get(metric_key(row['id']),{})
        remaining=max(0,int(m.get('last_success',0)+600-time.time()))
        paused=bool(m.get('failure_streak',0)>=2 and time.time()-m.get('last_failure_at',0)<NO_OUTPUT_PAUSE_SECONDS and row['id']!='linkedin')
        result.append({**row,'available':row['available'] and not paused,
                       'note':'Source failed in two recent searches; paused for one hour.' if paused else row.get('note',''),
                       'cooldown_seconds':remaining,'estimated_seconds':round(m.get('estimate',20),1),
                       'timing_samples':m.get('samples',0),'average_fetch_seconds':round(m['fetch_total']/m['fetch_samples'],1) if m.get('fetch_samples') else None})
    return sorted(result,key=lambda row:(not row['available'],row['estimated_seconds']))

def status(run_id):
    value=read('search-run:'+db.current_user()+':'+run_id)
    if not value:raise HTTPException(404,'Search not found')
    if value['state'] in {'queued','running'} and time.time()-value['updated_at']>SOURCE_TIMEOUT_SECONDS+120:
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
                    samples=metric.get('samples',0)
                    total=metric.get('total_seconds',metric.get('estimate',0)*samples)+elapsed
                    metric.update(estimate=total/(samples+1),total_seconds=total,samples=samples+1)
                    for report in reports:
                        if report.get('fetch_seconds') is not None and not report.get('cached'):
                            metric['fetch_total']=metric.get('fetch_total',0)+report['fetch_seconds']
                            metric['fetch_samples']=metric.get('fetch_samples',0)+1
                    if any(r.get('status')=='success' for r in reports):
                        metric['failure_streak']=0
                    elif any(r.get('status')=='unavailable' for r in reports):
                        if time.time()-metric.get('last_failure_at',0)>=NO_OUTPUT_PAUSE_SECONDS:
                            metric['failure_streak']=0
                        metric['failure_streak']=metric.get('failure_streak',0)+1
                        metric['last_failure_at']=time.time()
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
        try:
            _pool.submit(context.run,work)
        except Exception:
            # A shutting-down executor can reject the task after the run was
            # reserved. Release it so the user can retry on a healthy worker.
            _active.pop(user,None)
            value.update(state='failed',updated_at=time.time(),message='Search could not start. Please retry.')
            try:
                write(key,value)
            except Exception:
                pass
            raise HTTPException(503,'Search could not start. Please retry.')
        return {'run_id':run_id,'state':'queued'}
