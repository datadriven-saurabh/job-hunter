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
