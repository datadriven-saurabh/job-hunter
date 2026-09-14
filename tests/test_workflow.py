import os
import tempfile
os.environ["ENABLE_LOCAL_LLM"]="false"
os.environ["ENABLE_LIVE_SUBMISSION"]="false"

from fastapi.testclient import TestClient
from backend.main import app
from backend.agents.classifier import classify
from backend.agents.scout_agent import score
from backend.demo import PROFILE, CONFIG


def test_end_to_end():
    with TestClient(app) as client:
        assert client.get('/health').status_code==200
        assert client.post('/api/v1/demo').status_code==200
        jobs=client.get('/api/v1/applications').json()
        assert len(jobs)==8
        client.post('/api/v1/demo')
        assert len(client.get('/api/v1/applications').json())==8
        job=jobs[0]
        assert client.post('/api/v1/applications/batch-apply',json=[job['job_id']]).status_code==200
        updated=client.get('/api/v1/applications').json()[0]
        assert updated['status']=='TAILORED',updated['submission_logs']
        assert any(log['result']=='NEEDS_HUMAN' for log in updated['submission_logs'])
        pdf=client.get(f"/api/v1/applications/{job['job_id']}/document/resume")
        assert pdf.content.startswith(b'%PDF')
        context=client.get(f"/api/v1/extension/fill-context/{job['job_id']}").json()
        assert context['fields']['email']==PROFILE['personal_details']['email']
        assert client.patch(f"/api/v1/applications/{job['job_id']}",json={'status':'OFFER'}).status_code==409
        assert client.patch(f"/api/v1/applications/{job['job_id']}",json={'status':'APPLIED'}).status_code==200
        assert client.post('/api/v1/applications/batch-apply',json=[job['job_id']]).status_code==409
        qs=client.post('/api/v1/interview/generate-questions',params={'job_id':job['job_id']}).json()
        feedback=client.post('/api/v1/interview/evaluate',json={'job_id':job['job_id'],'question_id':qs[0]['id'],'answer':'At the time my task was to improve speed. I built a cache and reduced latency by 30%.'})
        assert feedback.status_code==200
        assert feedback.json()['score']==10
        assert client.get('/api/v1/applications',headers={'Origin':'https://evil.example'}).status_code==403
        assert client.get('/api/v1/extension/fill-context/missing').status_code==404
        assert client.post('/api/v1/applications/batch-apply',json=[]).status_code==400

def test_classifier_and_filters():
    assert classify({'job_url':'https://jobs.lever.co/company/123'})=='HEADLESS_AUTO'
    assert classify({'job_url':'https://jobs.lever.co.evil.test/company'})=='HUMAN_IN_THE_LOOP_LINK'
    assert classify({'job_url':'https://boards.greenhouse.io/company','description':'CAPTCHA required'})=='HUMAN_IN_THE_LOOP_LINK'
    criteria=dict(CONFIG['job_search_criteria'],dealbreaker_keywords=['clearance'])
    assert score({'job_title':'Software Engineer','location':'Remote','description':'Security clearance'},PROFILE,criteria) is None
    criteria=dict(CONFIG['job_search_criteria'],required_stack_keywords=['Rust'])
    assert score({'job_title':'Software Engineer','location':'Remote','description':'React'},PROFILE,criteria) is None

def test_profile_validation_and_manual_import():
    with TestClient(app) as client:
        client.post("/api/v1/demo")
        import copy
        profile=copy.deepcopy(PROFILE)
        profile['personal_details']['full_name']='  '
        assert client.post('/api/v1/profile',json=profile).status_code==422
        criteria=copy.deepcopy(CONFIG)
        criteria['job_search_criteria']['dealbreaker_keywords']=['   ']
        assert client.post('/api/v1/config',json=criteria).status_code==200
        assert client.get('/api/v1/config').json()['job_search_criteria']['dealbreaker_keywords']==[]
        body={'company_name':'Test Corp','job_title':'Software Engineer','job_url':'https://careers.example.com/123','location':'Remote','description':'Build applications with Python, React, SQL and TypeScript.'}
        assert client.post('/api/v1/jobs/import',json=body).json()['count']==1
        body['job_url']='javascript:alert(1)'
        assert client.post('/api/v1/jobs/import',json=body).status_code==400
        assert client.get('/health',headers={'host':'evil.example'}).status_code==400
        criteria['execution_preferences']['max_daily_applications']=1
        client.post('/api/v1/config',json=criteria)
        jobs=client.get('/api/v1/applications').json()
        assert client.post('/api/v1/applications/batch-apply',json=[j['job_id'] for j in jobs[:2]]).status_code==400


def test_optional_model_uses_only_source_bullets(monkeypatch):
    from backend.agents import tailor_agent
    from backend.demo import jobs
    import json
    monkeypatch.setattr(tailor_agent,'generate_json',lambda *args,**kwargs:{'bullets':['Invented an impossible achievement.']})
    job=dict(jobs()[0],job_id='grounding-test')
    resume,_=tailor_agent.tailor(job,PROFILE)
    from pathlib import Path
    document=json.loads(Path(resume).with_name('resume.json').read_text())
    contents=json.dumps(document)
    assert 'impossible achievement' not in contents
    assert 'Reduced page load time by 35%' in contents

def test_submission_requires_review_and_real_profile(monkeypatch):
    with TestClient(app) as client:
        client.post('/api/v1/demo')
        config=client.get('/api/v1/config').json()
        config['execution_preferences']['enable_headless_auto_apply']=True
        config['execution_preferences']['max_daily_applications']=20
        client.post('/api/v1/config',json=config)
        monkeypatch.setenv('ENABLE_LIVE_SUBMISSION','true')
        job=client.get('/api/v1/applications').json()[1]
        response=client.post('/api/v1/applications/batch-apply?submit=true',json=[job['job_id']])
        assert response.status_code==400
        assert 'demo profile' in response.json()['detail']
        # With headless enabled, ordinary preparation must still never submit.
        response=client.post('/api/v1/applications/batch-apply',json=[job['job_id']])
        assert response.status_code==200
        updated=next(j for j in client.get('/api/v1/applications').json() if j['job_id']==job['job_id'])
        assert updated['status']=='TAILORED'
