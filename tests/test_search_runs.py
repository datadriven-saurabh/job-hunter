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
