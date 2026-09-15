import io
import json
import zipfile
from fastapi.testclient import TestClient
from backend.main import app
from backend import database as db
from backend.demo import PROFILE
from backend.services import resumes
from backend.agents import job_sources
from backend.agents.scout_agent import job_id

DATA_RESUME=b'Sam Test\nData Analyst\nPython SQL Tableau Power BI statistics analytics\nBuilt SQL dashboards and analyzed customer retention using Python and Tableau.'
WEB_RESUME=b'Sam Test\nFrontend Engineer\nReact TypeScript JavaScript CSS HTML accessibility\nBuilt responsive interfaces with React and TypeScript and improved web accessibility.'

def test_upload_recommend_choose_and_prepare():
    with TestClient(app) as c:
        c.post('/api/v1/demo')
        a=c.post('/api/v1/resumes/upload',files={'file':('analytics.txt',DATA_RESUME,'text/plain')},data={'label':'Analytics CV'})
        b=c.post('/api/v1/resumes/upload',files={'file':('web.txt',WEB_RESUME,'text/plain')})
        assert a.status_code==b.status_code==200
        aid=a.json()['resume_id'];bid=b.json()['resume_id']
        assert 'sql' in a.json()['keywords']
        assert not c.post('/api/v1/resumes/upload',files={'file':('duplicate.txt',DATA_RESUME,'text/plain')}).json()['created']
        assert len(c.get('/api/v1/resumes').json())==3
        job={'company_name':'Analytics Test','job_title':'Data Analyst','job_url':'https://careers.example.com/analytics','description':'Use Python SQL Tableau Power BI statistics analytics to build dashboards and analyze customer retention.','location':'Remote'}
        c.post('/api/v1/jobs/import',json=job)
        id=job_id(job['job_url'])
        matches=c.get(f'/api/v1/applications/{id}/resume-matches').json()
        assert matches['recommended_resume_id']==aid,matches
        assert matches['matches'][0]['matched_keywords']
        assert c.post(f'/api/v1/applications/{id}/resume',json={'resume_id':aid}).status_code==200
        assert c.post('/api/v1/applications/batch-apply',json=[id]).status_code==200
        doc=c.get(f'/api/v1/applications/{id}/document/resume')
        assert doc.status_code == 404  # Unreviewed uploads cannot bypass the required template.
        assert c.get(f'/api/v1/resumes/{aid}/download').content==DATA_RESUME
        assert c.post(f'/api/v1/applications/{id}/resume',json={'resume_id':bid}).status_code==200
        assert db.get_job(id)['status']=='MATCHED'
        assert c.get(f'/api/v1/applications/{id}/document/resume').status_code==404
        c.patch(f'/api/v1/applications/{id}',json={'status':'APPLIED'})
        assert c.post(f'/api/v1/applications/{id}/resume',json={'resume_id':aid}).status_code==409

def test_file_validation_and_docx_extraction():
    with TestClient(app) as c:
        assert c.post('/api/v1/resumes/upload',files={'file':('x.exe',b'not a resume')}).status_code==400
        assert c.post('/api/v1/resumes/upload',files={'file':('bad.pdf',b'not a pdf')}).status_code==400
        assert c.post('/api/v1/resumes/upload',files={'file':('empty.txt',b'hello')}).status_code==400
        z=io.BytesIO()
        with zipfile.ZipFile(z,'w') as out:
            out.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Data analyst with Python SQL Tableau and experience building business intelligence dashboards.</w:t></w:r></w:p></w:body></w:document>')
        result=c.post('/api/v1/resumes/upload',files={'file':('../../resume.docx',z.getvalue())})
        assert result.status_code==200
        record=resumes.get(result.json()['resume_id'])
        assert record['original_name']=='resume.docx'
        assert 'tableau' in record['keywords']

def test_calendar_validation():
    import copy
    with TestClient(app) as c:
        p=copy.deepcopy(PROFILE)
        p['base_resume']['experience_history'][0]['start_date']='2022-13'
        assert c.post('/api/v1/profile',json=p).status_code==422
        p['base_resume']['experience_history'][0]['start_date']='2022-01'
        p['base_resume']['experience_history'][0]['end_date']='2021-12'
        assert c.post('/api/v1/profile',json=p).status_code==422
        p['base_resume']['experience_history'][0]['end_date']='Present'
        assert c.post('/api/v1/profile',json=p).status_code==200

def test_public_parsers():
    markup='''<li><div class="base-search-card"><a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/test-123?refId=x"></a><h3 class="base-search-card__title">Data Analyst</h3><h4 class="base-search-card__subtitle">Example</h4><span class="job-search-card__location">India</span></div></li>'''
    cards=job_sources.linkedin_cards(markup)
    assert cards[0]['job_title']=='Data Analyst'
    assert cards[0]['description_incomplete']
    assert '?' not in cards[0]['job_url']
    posting={'@context':'https://schema.org','@type':'JobPosting','title':'Engineer','description':'Python engineering role','url':'https://careers.example.com/123','hiringOrganization':{'name':'Example'},'jobLocationType':'TELECOMMUTE','employmentType':'FULL_TIME'}
    jobs=job_sources.jsonld_jobs('<script type="application/ld+json">'+json.dumps(posting)+'</script>')
    assert jobs[0]['location']=='Remote'
    assert jobs[0]['employment_type']=='Full-time'
    assert job_id('https://in.linkedin.com/jobs/view/some-title-123?refId=x')==job_id('https://www.linkedin.com/jobs/view/123')

def test_multisource_partial_failure_and_cache(monkeypatch):
    def retrieve(provider,**kwargs):
        if provider=='hiringcafe':raise job_sources.SourceUnavailable('Public access unavailable (HTTP 403).')
        return [{'company_name':'Public Board','job_title':'Software Engineer','job_url':'https://careers.example.com/live-1','location':'Remote','description':'Python React software engineering opportunity','employment_type':'Full-time','source':'LinkedIn'}]
    monkeypatch.setattr(job_sources,'retrieve',retrieve)
    with TestClient(app) as c:
        c.post('/api/v1/demo')
        r=c.post('/api/v1/jobs/search',json={'sources':['linkedin','hiringcafe'],'location':'Remote','keywords':'Software Engineer'})
        assert r.status_code==200
        result=r.json()
        assert result['count']==1
        assert result['sources'][1]['status']=='unavailable'
        assert '403' in result['sources'][1]['message']
        r=c.post('/api/v1/jobs/search',json={'sources':['linkedin','hiringcafe'],'location':'Remote','keywords':'Software Engineer'})
        assert r.json()['sources'][0]['cached']

def test_public_feeds_preserve_attribution_and_cache(monkeypatch):
    db.init_db()
    calls=[]
    class Response:
        text='<rss><channel><item><title>Example Co: Data Analyst</title><link>https://weworkremotely.com/remote-jobs/example</link><description>SQL Python dashboards</description><region>Europe</region></item></channel></rss>'
        def json(self):return [{'legal':'metadata'}, {'company':'Example Co','position':'Data Analyst','url':'https://remoteOK.com/remote-jobs/example','description':'SQL Python dashboards','location':'Europe'}]
    monkeypatch.setattr(job_sources,'public_get',lambda url:(calls.append(url) or Response()))
    for provider,host in [('remoteok','remoteok.com'),('wwr','weworkremotely.com')]:
        jobs=job_sources.retrieve(provider,keywords='Data Analyst')
        assert len(jobs)==1 and host in jobs[0]['source_url'].lower()
        assert 'Remote' in jobs[0]['location']
        assert job_sources.retrieve(provider,keywords='Python')
    assert len(calls)==2
    import pytest
    with pytest.raises(job_sources.SourceUnavailable):job_sources.wwr_jobs('<!DOCTYPE rss><rss/>')
