from fastapi.testclient import TestClient
from backend.main import app
from backend import database as db
import json


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


def test_review_queue_is_separate_and_rediscovery_does_not_replace_it(monkeypatch):
    import backend.studio_api as studio
    monkeypatch.setattr(studio,'generate_review',lambda job_id,token:None)
    with TestClient(app) as c:
        c.post('/api/v1/demo')
        job=c.get('/api/v1/applications?phase=new').json()[0]
        moved=c.post('/api/v1/applications/review',json={'job_ids':[job['job_id']]})
        assert moved.status_code==200
        assert job['job_id'] not in [row['job_id'] for row in c.get('/api/v1/applications?phase=new').json()]
        reviewing=c.get('/api/v1/applications?phase=reviewing').json()
        assert [row['job_id'] for row in reviewing]==[job['job_id']]
        c.post('/api/v1/demo')
        assert db.get_job(job['job_id'])['status']=='REVIEWING'
        assert c.post('/api/v1/applications/review',json={'job_ids':[job['job_id']]}).status_code==200
        assert len(db.query('SELECT * FROM studio_runs WHERE job_id=:id',{'id':job['job_id']}))==1


def test_restart_keeps_interrupted_review_job_in_reviewing(monkeypatch):
    import backend.studio_api as studio
    monkeypatch.setattr(studio,'generate_review',lambda job_id,token:None)
    with TestClient(app) as c:
        c.post('/api/v1/demo');job=c.get('/api/v1/applications?phase=new').json()[0]
        c.post('/api/v1/applications/review',json={'job_ids':[job['job_id']]})
        db.execute("UPDATE application_records SET status='QUEUED' WHERE job_id=:id",{'id':job['job_id']})
    with TestClient(app) as c:
        restored=db.get_job(job['job_id'])
        assert restored['status']=='REVIEWING'
        assert restored['studio_state']=='failed'


def test_deleting_opportunity_removes_only_its_workspace_files():
    with TestClient(app) as c:
        c.post('/api/v1/demo');jobs=c.get('/api/v1/applications').json()[:2]
        for index,job in enumerate(jobs):
            kit_id=f'{index+1:032x}';folder=db.DATA/'kits'/kit_id;folder.mkdir(parents=True)
            (folder/'kit.json').write_text(json.dumps({'id':kit_id,'job':{'job_id':job['job_id']},'assets':{}}))
            db.execute('INSERT INTO studio_kits(kit_id,job_id) VALUES (:kit,:job)',{'kit':kit_id,'job':job['job_id']})
        removed=db.DATA/'kits'/f'{1:032x}';kept=db.DATA/'kits'/f'{2:032x}'
        assert c.post('/api/v1/applications/delete',json={'job_ids':[jobs[0]['job_id']]}).status_code==200
        assert not removed.exists() and kept.exists()
        assert c.get(f'/api/v1/studio/kits/{1:032x}').status_code==404
        assert c.get(f'/api/v1/studio/kits/{2:032x}').status_code==200
