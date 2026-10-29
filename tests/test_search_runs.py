import time
import pytest
from fastapi import HTTPException
from backend.services import search_runs as runs
from backend.main import SearchRequest

ROWS=[{'id':str(i),'name':str(i),'available':True,'kind':'public-search'} for i in range(4)]

def test_limit_cooldown_and_estimate(monkeypatch):
    with pytest.raises(HTTPException) as exc:runs.start(SearchRequest(sources=['0','1','2','3']),lambda _:None,ROWS)
    assert exc.value.status_code==400
    runs.write(runs.metric_key('0'),{'last_success':time.time(),'estimate':20})
    with pytest.raises(HTTPException) as exc:runs.start(SearchRequest(sources=['0']),lambda _:None,ROWS)
    assert exc.value.status_code==429
    runs.write(runs.metric_key('1'),{'estimate':65})
    class Queued:
        def submit(self, fn, *args):self.task=lambda:fn(*args)
    pool=Queued();monkeypatch.setattr(runs,'_pool',pool)
    result=runs.start(SearchRequest(sources=['1']),lambda _: {'count':0,'sources':[{'source':'1','status':'success','fetch_seconds':65}]},ROWS)
    assert result['state']=='queued'
    pool.task()
    assert runs.status(result['run_id'])['state']=='complete'
    assert next(r for r in runs.catalog(ROWS) if r['id']=='1')['average_fetch_seconds']==65

def test_progress_saved_and_success_cools_down(monkeypatch):
    class Immediate:
        def submit(self,fn,*args):
            # Queue for execution after start releases its lock.
            self.task=lambda:fn(*args)
    pool=Immediate();monkeypatch.setattr(runs,'_pool',pool)
    result=runs.start(SearchRequest(sources=['2']),lambda _: {'count':2,'sources':[{'source':'2','status':'success'}]},ROWS)
    assert runs.status(result['run_id'])['state']=='queued'
    pool.task()
    saved=runs.status(result['run_id'])
    assert saved['state']=='complete' and saved['count']==2
    assert next(r for r in runs.catalog(ROWS) if r['id']=='2')['cooldown_seconds']>590

def test_endpoint_returns_progress_and_rejects_manual_boards(monkeypatch):
    from fastapi.testclient import TestClient
    from backend.main import app
    class Queued:
        def submit(self, fn, *args): self.task=lambda:fn(*args)
    pool=Queued();monkeypatch.setattr(runs,'_pool',pool)
    with TestClient(app) as client:
        client.post('/api/v1/demo')
        assert client.post('/api/v1/jobs/search-runs',json={'sources':['greenhouse']}).status_code==400
        response=client.post('/api/v1/jobs/search-runs',json={'sources':['remoteok']})
        assert response.status_code==202
        run_id=response.json()['run_id']
        assert client.get('/api/v1/jobs/search-runs/'+run_id).json()['state']=='queued'
        assert client.post('/api/v1/jobs/search-runs',json={'sources':['wwr']}).json()['run_id']==run_id
        # Simulate a process restart rather than running a network fetch.
        runs._active.clear()
        saved=runs.status(run_id);saved['updated_at']=time.time()-runs.SOURCE_TIMEOUT_SECONDS-121
        runs.write('search-run:'+runs.db.current_user()+':'+run_id,saved)
        assert client.get('/api/v1/jobs/search-runs/'+run_id).json()['state']=='interrupted'
        assert client.get('/api/v1/jobs/search-runs/not-a-run').status_code==404

def test_empty_search_does_not_pause_source_but_repeated_failures_do(monkeypatch):
    class Queued:
        def submit(self,fn,*args):self.task=lambda:fn(*args)
    pool=Queued();monkeypatch.setattr(runs,'_pool',pool)
    body=SearchRequest(sources=['3'])
    def empty(_):return {'count':0,'sources':[{'source':'3','status':'success','fetched':0,'cached':False}]}
    for _ in range(2):
        result=runs.start(body,empty,ROWS)
        assert result['state']=='queued'
        pool.task()
        metric=runs.read(runs.metric_key('3'))
        metric['last_success']=0
        runs.write(runs.metric_key('3'),metric)
    assert next(row for row in runs.catalog(ROWS) if row['id']=='3')['available'] is True
    def unavailable(_):return {'count':0,'sources':[{'source':'3','status':'unavailable','fetched':0}]}
    for _ in range(2):
        result=runs.start(body,unavailable,ROWS)
        assert result['state']=='queued'
        pool.task()
    assert next(row for row in runs.catalog(ROWS) if row['id']=='3')['available'] is False
    metric=runs.read(runs.metric_key('3'))
    metric['last_failure_at']=time.time()-runs.NO_OUTPUT_PAUSE_SECONDS-1
    runs.write(runs.metric_key('3'),metric)
    assert next(row for row in runs.catalog(ROWS) if row['id']=='3')['available'] is True
    result=runs.start(body,empty,ROWS)
    pool.task()
    assert runs.read(runs.metric_key('3'))['failure_streak']==0
    linkedin={'id':'linkedin','name':'LinkedIn','available':True,'kind':'public-search'}
    runs.write(runs.metric_key('linkedin'),dict(metric,last_failure_at=time.time()))
    assert runs.catalog([linkedin])[0]['available'] is True

def test_rejected_worker_submission_releases_active_run(monkeypatch):
    rows=[{'id':'rejected-worker','name':'Rejected worker','available':True,'kind':'public-search'}]
    ids=iter(['rejected-worker-run','retry-worker-run'])
    monkeypatch.setattr(runs.uuid,'uuid4',lambda: type('RunId',(),{'hex':next(ids)})())
    class Rejected:
        def submit(self, fn, *args):
            raise RuntimeError('executor has shut down')

    monkeypatch.setattr(runs,'_pool',Rejected())
    with pytest.raises(HTTPException) as exc:
        runs.start(SearchRequest(sources=['rejected-worker']),lambda _:None,rows)
    assert exc.value.status_code==503
    assert runs.db.current_user() not in runs._active
    assert runs.status('rejected-worker-run')['state']=='failed'

    class Queued:
        def submit(self, fn, *args):
            self.task=lambda:fn(*args)

    pool=Queued()
    monkeypatch.setattr(runs,'_pool',pool)
    result=runs.start(SearchRequest(sources=['rejected-worker']),lambda _: {'count':0,'sources':[{'source':'rejected-worker','status':'success'}]},rows)
    assert result['state']=='queued'
    pool.task()
    assert runs.status(result['run_id'])['state']=='complete'


def test_stale_run_releases_slot_and_late_worker_cannot_replace_retry(monkeypatch):
    rows=[{'id':'stale-a','name':'Stale A','available':True,'kind':'public-search'},
          {'id':'stale-b','name':'Stale B','available':True,'kind':'public-search'}]
    class Queued:
        def __init__(self):self.tasks=[]
        def submit(self,fn,*args):self.tasks.append(lambda:fn(*args))
    pool=Queued();monkeypatch.setattr(runs,'_pool',pool)
    old_id=None
    retry=None
    def delayed_search(_):
        nonlocal retry
        key='search-run:'+runs.db.current_user()+':'+old_id
        value=runs.read(key)
        value['updated_at']=time.time()-runs.SOURCE_TIMEOUT_SECONDS-121
        runs.write(key,value)
        assert runs.status(old_id)['state']=='interrupted'
        retry=runs.start(SearchRequest(sources=['stale-b']),lambda _: {'count':1,'sources':[{'source':'stale-b','status':'success'}]},rows)
        return {'count':1,'sources':[{'source':'stale-a','status':'success'}]}

    old=runs.start(SearchRequest(sources=['stale-a']),delayed_search,rows)
    old_id=old['run_id']
    pool.tasks[0]()
    assert runs.status(old_id)['state']=='interrupted'
    assert runs._active[runs.db.current_user()]==retry['run_id']
    pool.tasks[1]()
    assert runs.status(retry['run_id'])['state']=='complete'


def test_start_replaces_stale_run_without_status_poll(monkeypatch):
    rows=[{'id':'stale-retry','name':'Stale retry','available':True,'kind':'public-search'}]
    class Queued:
        def submit(self,fn,*args):self.task=lambda:fn(*args)
    pool=Queued();monkeypatch.setattr(runs,'_pool',pool)
    body=SearchRequest(sources=['stale-retry'])
    old=runs.start(body,lambda _:None,rows)
    user=runs.db.current_user()
    key='search-run:'+user+':'+old['run_id']
    saved=runs.read(key)
    saved['updated_at']=time.time()-runs.SOURCE_TIMEOUT_SECONDS-121
    runs.write(key,saved)

    retry=runs.start(body,lambda _: {'count':1,'sources':[{'source':'stale-retry','status':'success'}]},rows)
    assert retry['run_id']!=old['run_id']
    assert runs.status(old['run_id'])['state']=='interrupted'
    pool.task()
    assert runs.status(retry['run_id'])['state']=='complete'


def test_new_user_can_start_when_other_users_abandon_stale_runs(monkeypatch):
    rows=[{'id':'capacity-stale','name':'Capacity stale','available':True,'kind':'public-search'}]
    class Queued:
        def __init__(self):self.tasks=[]
        def submit(self,fn,*args):self.tasks.append(lambda:fn(*args))

    pool=Queued();monkeypatch.setattr(runs,'_pool',pool)
    monkeypatch.setattr(runs,'_active',{})
    monkeypatch.setattr(runs,'_active_updated',{},raising=False)
    saved={}
    monkeypatch.setattr(runs,'read',lambda key:saved.get(key))
    monkeypatch.setattr(runs,'write',lambda key,value:saved.__setitem__(key,dict(value)))
    monkeypatch.setattr(runs.db,'query',lambda *args,**kwargs:[])
    current=['first']
    monkeypatch.setattr(runs.db,'current_user',lambda:current[0])
    body=SearchRequest(sources=['capacity-stale'])
    first=runs.start(body,lambda _:None,rows)
    current[0]='second'
    second=runs.start(body,lambda _:None,rows)
    current[0]='third'
    with pytest.raises(HTTPException) as exc:
        runs.start(body,lambda _:None,rows)
    assert exc.value.status_code==429
    for user,run in [('first',first),('second',second)]:
        key='search-run:'+user+':'+run['run_id']
        saved[key]['updated_at']=time.time()-runs.SOURCE_TIMEOUT_SECONDS-121
        runs._active_updated[user]=time.monotonic()-runs.SOURCE_TIMEOUT_SECONDS-121

    third=runs.start(body,lambda _:{'count':1,'sources':[{'source':'capacity-stale','status':'success'}]},rows)
    assert third['run_id'] not in {first['run_id'],second['run_id']}
    pool.tasks[0]()  # The old worker cannot publish progress after losing its slot.
    current[0]='first'
    assert runs.status(first['run_id'])['state']=='interrupted'
    current[0]='third'
    pool.tasks[2]()
    assert runs.status(third['run_id'])['state']=='complete'
