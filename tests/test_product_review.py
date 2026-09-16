"""Regressions found by the product audit. All profiles and jobs are synthetic."""
import asyncio
import copy
import json
from pathlib import Path
from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend import database as db
from backend.demo import PROFILE, CONFIG, jobs as demo_jobs
from backend.agents import job_sources, orchestrator, apply_agent
from backend.agents.scout_agent import job_id
from backend.services.job_matching import assess
from backend.services.job_intelligence import language_requirements


def test_profile_concurrent_editor_cannot_overwrite_new_facts():
    with TestClient(app) as c:
        c.post('/api/v1/demo')
        first=c.get('/api/v1/profile').json();stale=copy.deepcopy(first)
        first['personal_details']['phone']='+15550005555'
        result=c.post('/api/v1/profile',json=first,headers={'If-Match':first['_revision']})
        assert result.status_code==200 and result.json()['_revision']!=first['_revision']
        stale['base_resume']['structured_skills'].append('New skill')
        assert c.post('/api/v1/profile',json=stale,headers={'If-Match':stale['_revision']}).status_code==409
        assert c.get('/api/v1/profile').json()['personal_details']['phone']=='+15550005555'
        preflight=c.options('/api/v1/profile',headers={'Origin':'http://localhost:3000','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'content-type,if-match'})
        assert preflight.status_code==200


def test_preparation_defaults_to_profile_despite_better_upload():
    with TestClient(app) as c:
        c.post('/api/v1/demo');job=c.get('/api/v1/applications').json()[0]
        c.post('/api/v1/resumes/upload',files={'file':('perfect.txt',(job['job_title']+' '+job['description']).encode(),'text/plain')})
        assert c.post('/api/v1/applications/batch-apply',json=[job['job_id']]).status_code==200
        updated=db.get_job(job['job_id'])
        assert updated['selected_resume_id']=='profile' and updated['status']=='TAILORED'
        assert Path(updated['tailored_resume_path']).is_file()


def test_batch_validation_does_not_partially_queue():
    with TestClient(app) as c:
        c.post('/api/v1/demo');jobs=c.get('/api/v1/applications').json()[:2]
        upload=c.post('/api/v1/resumes/upload',files={'file':('other.txt',b'Synthetic candidate with Python SQL and business intelligence experience in analytics.','text/plain')}).json()
        c.post(f"/api/v1/applications/{jobs[1]['job_id']}/resume",json={'resume_id':upload['resume_id']})
        assert c.post('/api/v1/applications/batch-apply',json=[j['job_id'] for j in jobs]).status_code==409
        assert all(db.get_job(j['job_id'])['status']=='MATCHED' for j in jobs)


def test_restart_retains_reviewed_document_and_uncertain_submission():
    with TestClient(app) as c:
        c.post('/api/v1/demo');id=c.get('/api/v1/applications').json()[0]['job_id']
        db.execute("UPDATE application_records SET status='QUEUED',tailored_resume_path='synthetic.pdf',submission_logs_json=:logs WHERE job_id=:id",{'id':id,'logs':json.dumps([{'action':'Submission attempt started; outcome unconfirmed','result':'NEEDS_HUMAN'}])})
    with TestClient(app) as c:
        assert db.get_job(id)['status']=='TAILORED'
        assert c.post('/api/v1/applications/batch-apply',json=[id]).status_code==409


def test_submission_stays_reserved_until_browser_finishes(monkeypatch):
    with TestClient(app) as c:
        c.post('/api/v1/demo');job=c.get('/api/v1/applications').json()[0];id=job['job_id']
        payload=json.loads(db.query('SELECT payload FROM job_details WHERE job_id=:id',{'id':id})[0]['payload']);payload['demo']=False
        db.execute('UPDATE job_details SET payload=:p WHERE job_id=:id',{'p':json.dumps(payload),'id':id})
        db.execute("UPDATE application_records SET status='QUEUED',classification='HEADLESS_AUTO',tailored_resume_path='synthetic.pdf' WHERE job_id=:id",{'id':id})
        config=c.get('/api/v1/config').json();config['execution_preferences']['enable_headless_auto_apply']=True;c.post('/api/v1/config',json=config)
        monkeypatch.setenv('ENABLE_LIVE_SUBMISSION','true')
        page=AsyncMock();page.locator.return_value=AsyncMock();page.locator.return_value.count.return_value=0
        browser=AsyncMock();browser.new_page.return_value=page
        pw=AsyncMock();pw.chromium.launch.return_value=browser
        manager=AsyncMock();manager.__aenter__.return_value=pw
        monkeypatch.setattr(apply_agent,'async_playwright',lambda:manager)
        async def interrupted(page,data,resume,before_submit=None):
            assert db.get_job(id)['status']=='QUEUED'
            assert c.post('/api/v1/applications/delete',json={'job_ids':[id]}).status_code==409
            assert c.post(f'/api/v1/applications/{id}/resume',json={'resume_id':'profile'}).status_code==409
            before_submit()
            raise RuntimeError('Synthetic click timeout after dispatch')
        # Locator() is synchronous in Playwright.
        from unittest.mock import Mock
        page.locator=Mock(return_value=AsyncMock());page.locator.return_value.count.return_value=0
        monkeypatch.setattr(apply_agent,'fill_and_submit',interrupted)
        asyncio.run(apply_agent.run_batch([id],submit=True))
        assert db.get_job(id)['status']=='TAILORED'
        assert any('unconfirmed' in l['action'] for l in db.get_job(id)['submission_logs'])
        assert c.post('/api/v1/applications/batch-apply',json=[id]).status_code==409


def test_repeated_search_skips_seen_and_deleted_jobs(monkeypatch):
    posting=dict(demo_jobs()[0],job_url='https://careers.example.com/new')
    monkeypatch.setattr(job_sources,'retrieve',lambda *a,**k:[posting])
    with TestClient(app) as c:
        c.post('/api/v1/profile',json=PROFILE)
        first=c.post('/api/v1/jobs/search',json={'provider':'remoteok'}).json()
        assert first['count']==1
        c.post('/api/v1/applications/delete',json={'job_ids':[job_id(posting['job_url'])]})
        second=c.post('/api/v1/jobs/search',json={'provider':'remoteok'}).json()
        assert second['count']==0 and second['sources'][0]['already_seen']==1
        assert c.get('/api/v1/applications').json()==[]


def test_candidate_limit_prefers_unseen_jobs_in_cached_pool(monkeypatch):
    postings=[dict(demo_jobs()[0],job_url='https://careers.example.com/'+str(i),company_name='Example '+str(i)) for i in range(3)]
    monkeypatch.setattr(job_sources,'retrieve',lambda *a,**k:postings)
    with TestClient(app) as c:
        c.post('/api/v1/profile',json=PROFILE)
        for i in range(3):
            r=c.post('/api/v1/jobs/search',json={'provider':'remoteok','limit':1}).json()
            assert r['count']==1,r
        assert len(c.get('/api/v1/applications').json())==3
        assert c.post('/api/v1/jobs/search',json={'provider':'remoteok','limit':1}).json()['count']==0


def test_new_filters_can_reconsider_previously_excluded_job():
    posting=dict(demo_jobs()[0],location='Berlin')
    state={'jobs':[posting],'profile':PROFILE,'criteria':dict(CONFIG['job_search_criteria'],target_locations=['India']),'skip_seen':True}
    assert orchestrator.discovery_graph.invoke(state)['count']==0
    assert orchestrator.discovery_graph.invoke(state)['skipped']==1
    state['criteria']['target_locations']=['Berlin']
    # Direct graph tests must create the owning profile before persistence.
    with TestClient(app) as c:c.post('/api/v1/profile',json=PROFILE)
    assert orchestrator.discovery_graph.invoke(state)['count']==1


def test_job_identity_preserves_requisition_query():
    assert job_id('https://example.com/job?reference=1')!=job_id('https://example.com/job?reference=2')
    assert job_id('https://example.com/job?id=1&utm_source=x')==job_id('https://example.com/job?id=1')
    assert job_id('https://notlinkedin.com/123')!=job_id('https://linkedin.com/123')


def test_language_levels_and_negated_requirements():
    p=copy.deepcopy(PROFILE);p['base_resume']['languages']=[{'language':'German','level':'C1'},{'language':'English','level':'C1'}]
    job=dict(demo_jobs()[0],description=demo_jobs()[0]['description']+' German C1 required; English C1 required. Rust is not required.')
    fit=assess(job,p,CONFIG['job_search_criteria'])
    assert not any('Verify language' in w for w in fit['warnings'])
    assert 'Rust' not in fit['missing_skills']
    rules=language_requirements('English C1 required; German is preferred. French is not required.')
    assert [(r['language'],r['importance']) for r in rules]==[('English','required'),('German','preferred')]


def test_public_page_links_are_bounded_and_do_not_refetch_saved(monkeypatch):
    from backend.agents.public_boards import posting_links,public_page_jobs
    url='https://builtin.com/job/data-analyst/123'
    assert posting_links('<a href="https://evil.example/job/a/1">x</a><a href="'+url+'">x</a>', 'https://builtin.com/jobs',r'/job/[^/]+/\d+',{'builtin.com'})==[url]
    calls=[]
    class Response:
        def __init__(self,text):self.text=text
    def fetch(target):
        calls.append(target)
        if target.endswith('/jobs'):return Response('<a href="'+url+'">Data analyst</a>')
        return Response('<script type="application/ld+json">'+json.dumps({'@type':'JobPosting','title':'Data Analyst','hiringOrganization':{'name':'Example'},'description':'Analyze SQL data and build dashboards. '*15,'url':url})+'</script>')
    monkeypatch.setattr(job_sources,'public_get',fetch)
    with TestClient(app) as c:
        c.post('/api/v1/profile',json=PROFILE)
        posting=public_page_jobs('builtin',limit=1)[0]
        c.post('/api/v1/jobs/import',json=posting)
        public_page_jobs('builtin',limit=1)
    assert calls.count(url)==1


def test_whole_directory_available_to_discovery():
    expected={'hackernews','yc','wellfound','builtin','aijobs','indeed','glassdoor','google','workable','stepstone'}
    assert expected<={s['id'] for s in job_sources.SOURCE_INFO}


def test_model_routing_normalizes_latest_and_disabled_benchmark_rejected(monkeypatch):
    from backend import model_api
    monkeypatch.setattr(model_api,'tags',lambda:[{'name':'nomic-embed-text:latest'}])
    with TestClient(app) as c:
        c.post('/api/v1/profile',json=PROFILE)
        r=c.put('/api/v1/career/model-routing',json={'model_tiers':{'embedding':'nomic-embed-text'}})
        assert r.status_code==200 and r.json()['tiers']['embedding']=='nomic-embed-text:latest'
        assert c.post('/api/v1/models/compare',json={'models':['nomic-embed-text:latest']}).status_code==409


def test_machine_learning_is_not_mistaken_for_aspirational_skill():
    from backend.services.job_matching import affirmed_skills
    assert 'Machine learning' in affirmed_skills('Built machine learning models with Python.')
    assert 'Python' not in affirmed_skills('I am learning Python.')
