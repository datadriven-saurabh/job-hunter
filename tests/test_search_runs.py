import time
import pytest
from fastapi import HTTPException
from backend.services import search_runs as runs
from backend.main import SearchRequest

ROWS=[{'id':str(i),'name':str(i),'available':True,'kind':'public-search'} for i in range(4)]

def test_limit_cooldown_and_estimate():
    with pytest.raises(HTTPException) as exc:runs.start(SearchRequest(sources=['0','1','2','3']),lambda _:None,ROWS)
    assert exc.value.status_code==400
    runs.write(runs.metric_key('0'),{'last_success':time.time(),'estimate':20})
    with pytest.raises(HTTPException) as exc:runs.start(SearchRequest(sources=['0']),lambda _:None,ROWS)
    assert exc.value.status_code==429
    runs.write(runs.metric_key('1'),{'estimate':65})
    with pytest.raises(HTTPException):runs.start(SearchRequest(sources=['1']),lambda _:None,ROWS)

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
        saved=runs.status(run_id);saved['updated_at']=time.time()-301
        runs.write('search-run:'+runs.db.current_user()+':'+run_id,saved)
        assert client.get('/api/v1/jobs/search-runs/'+run_id).json()['state']=='interrupted'
        assert client.get('/api/v1/jobs/search-runs/not-a-run').status_code==404
