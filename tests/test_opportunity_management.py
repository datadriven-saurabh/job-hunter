from fastapi.testclient import TestClient
from backend.main import app
from backend import database as db


def test_delete_restore_and_rediscovery():
    with TestClient(app) as c:
        c.post('/api/v1/demo')
        before=c.get('/api/v1/applications').json();job=before[0];id=job['job_id']
        assert c.post('/api/v1/applications/delete',json={'job_ids':[id,id]}).json()['deleted']==[id]
        assert len(c.get('/api/v1/applications').json())==len(before)-1
        assert db.get_job(id) is None
        assert c.post('/api/v1/applications/batch-apply',json=[id]).status_code==404
        c.post('/api/v1/demo')
        assert id not in [j['job_id'] for j in c.get('/api/v1/applications').json()]
        assert c.get('/api/v1/applications/deleted').json()[0]['job_id']==id
        assert c.post('/api/v1/applications/restore',json={'job_ids':[id]}).status_code==200
        assert db.get_job(id)['status']==job['status']
        assert c.get('/api/v1/applications/deleted').json()==[]


def test_delete_batch_atomic_and_queued_protected():
    with TestClient(app) as c:
        c.post('/api/v1/demo');jobs=c.get('/api/v1/applications').json();ids=[j['job_id'] for j in jobs[:2]]
        assert c.post('/api/v1/applications/delete',json={'job_ids':[ids[0],'absent']}).status_code==404
        assert c.get('/api/v1/applications/deleted').json()==[]
        db.execute("UPDATE application_records SET status='QUEUED' WHERE job_id=:id",{'id':ids[1]})
        assert c.post('/api/v1/applications/delete',json={'job_ids':ids}).status_code==409
        assert c.get('/api/v1/applications/deleted').json()==[]
        assert c.post('/api/v1/applications/delete',json={'job_ids':[]}).status_code==422
        assert c.post('/api/v1/applications/delete',json={'job_ids':['x']*101}).status_code==422
