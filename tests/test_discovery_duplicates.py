import json

from fastapi.testclient import TestClient
from backend import database as db
from backend.agents.orchestrator import _persist
from backend.demo import PROFILE
from backend.main import app


def test_equal_quality_workable_duplicate_keeps_match_fields():
    with TestClient(app) as client:
        assert client.post('/api/v1/profile',json=PROFILE).status_code==200
    original={
        'company_name':'Example Co', 'job_title':'Digital Marketing Manager',
        'job_url':'https://jobs.workable.com/view/original/example',
        'location':'Remote', 'description':'Manage digital campaigns and growth reporting. Coordinate channel strategy, measure conversion performance, and improve acquisition across regions and products.',
        'source':'Workable', 'first_seen_at':'2026-09-01T00:00:00+00:00',
    }
    db.execute("INSERT INTO application_records(job_id,user_id,company_name,job_title,job_url,match_score,classification,status) VALUES ('original','local',:company_name,:job_title,:job_url,0.5,'MANUAL','MATCHED')",original)
    db.execute('INSERT INTO job_details(job_id,payload) VALUES (:id,:payload)',{'id':'original','payload':json.dumps({k:v for k,v in original.items() if k not in {'company_name','job_title','job_url'}})})
    incoming=dict(original,job_id='new-workable-card',job_url='https://jobs.workable.com/view/another/example',match_score=0.74,classification='HUMAN_IN_THE_LOOP_LINK')

    result=_persist({'matched':[incoming],'profile':{'user_id':'local'},'seen':[],'skipped':0})

    assert result['count']==0
    saved=db.query("SELECT match_score FROM application_records WHERE job_id='original'")[0]
    assert saved['match_score']==0.74
    details=json.loads(db.query("SELECT payload FROM job_details WHERE job_id='original'")[0]['payload'])
    assert {item['url'] for item in details['alternative_sources']}=={original['job_url'],incoming['job_url']}
