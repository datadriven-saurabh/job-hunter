"""Context.dev discovery stays bounded and never calls the live API in tests."""
from types import SimpleNamespace

from fastapi.testclient import TestClient

from backend.agents import job_sources
from backend.main import app
from backend.services import context_dev
from backend.services import search_runs


def result(title, url, markdown='Build reliable Python and TypeScript software with React. ' * 8):
    return {'title':title,'url':url,'snippet':'A public job posting.','markdown':markdown}


def test_context_wrapper_bounds_search_and_uses_server_key(monkeypatch):
    monkeypatch.setenv('CONTEXT_DEV_API_KEY','test-only')
    calls=[]
    class Client:
        def __init__(self,**options):
            calls.append(options)
            self.web=self
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def search(self,**options):
            calls.append(options)
            item=SimpleNamespace(url='https://jobs.ashbyhq.com/example/123',title='Software Engineer at Example',
                                 description='Example job',markdown=SimpleNamespace(code='SUCCESS',markdown='Full posting'))
            return SimpleNamespace(results=[item],partial=False,request_id='synthetic-request',
                                   key_metadata=SimpleNamespace(credits_consumed=2))
    monkeypatch.setattr(context_dev,'ContextDev',Client)
    response=context_dev.search_web('Software Engineer jobs')
    assert calls[0]['api_key']=='test-only' and calls[0]['max_retries']==1
    assert calls[1]['num_results']==10
    assert calls[1]['include_domains']==context_dev.JOB_DOMAINS
    assert calls[1]['markdown_options']['max_age_ms']==7*24*60*60*1000
    assert response['credits_used']==2 and response['results'][0]['markdown']=='Full posting'


def test_context_source_requires_key_and_search_terms(monkeypatch):
    monkeypatch.delenv('CONTEXT_DEV_API_KEY', raising=False)
    assert not next(source for source in job_sources.source_catalog(True) if source['id']=='contextdev')['available']
    try:
        context_dev.search_web('Software Engineer jobs')
    except context_dev.ContextSearchError as exc:
        assert 'CONTEXT_DEV_API_KEY' in str(exc)
    else:
        assert False, 'Missing key must fail before any API call.'
    monkeypatch.setenv('CONTEXT_DEV_API_KEY','test-only')
    assert next(source for source in job_sources.source_catalog() if source['id']=='contextdev')['available']
    try:
        job_sources.context_jobs('')
    except job_sources.SourceUnavailable as exc:
        assert 'keywords' in str(exc)
    else:
        assert False, 'An empty query must not spend credits.'


def test_context_results_keep_direct_postings_without_invented_facts(monkeypatch):
    queries=[]
    def search(query):
        queries.append(query)
        return {'results':[
            result('Software Engineer at Example Co','https://jobs.ashbyhq.com/example/123'),
            result('Software Engineer guide','https://blog.example.com/software-engineer-guide'),
            result('Software Engineer job openings','https://careers.cisco.com/global/en/search-results?keywords=software'),
            result('Best Software Engineer Jobs','https://www.builtinboston.com/jobs/dev-engineering'),
            result('Software Engineer jobs','https://jobs.lever.co/other'),
            result('Product Manager at Other Co','https://jobs.lever.co/other/456'),
            result('Software Engineer at Bad Co','http://jobs.bad.example/789'),
            result('Software Engineer at Brief Co','https://jobs.lever.co/brief/555',None),
        ]}
    monkeypatch.setattr(context_dev,'search_web',search)
    jobs=job_sources.context_jobs('Software Engineer','Berlin',limit=10)
    assert queries==['"Software Engineer" Berlin job opening apply']
    assert len(jobs)==2
    assert jobs[0]['job_title']=='Software Engineer' and jobs[0]['company_name']=='Example Co'
    assert jobs[0]['location']=='' and jobs[0]['posted_at'] is None
    assert jobs[0]['source_url']==jobs[0]['job_url']
    assert not jobs[0]['description_incomplete']
    assert jobs[1]['description_incomplete']


def test_context_source_uses_existing_profile_matching_pipeline(monkeypatch):
    monkeypatch.setenv('CONTEXT_DEV_API_KEY','test-only')
    monkeypatch.setattr(context_dev,'search_web',lambda query:{'results':[
        result('Software Engineer at Example Co','https://jobs.ashbyhq.com/example/123')
    ]})
    class Queued:
        def submit(self,fn,*args):self.task=lambda:fn(*args)
    pool=Queued()
    monkeypatch.setattr(search_runs,'_pool',pool)
    with TestClient(app) as client:
        assert client.post('/api/v1/demo').status_code==200
        sources=client.get('/api/v1/jobs/sources').json()
        assert next(source for source in sources if source['id']=='contextdev')['available']
        started=client.post('/api/v1/jobs/search-runs',json={'sources':['contextdev'],'keywords':'Software Engineer'})
        assert started.status_code==202
        pool.task()
        response=client.get('/api/v1/jobs/search-runs/'+started.json()['run_id']).json()
        assert response['state']=='complete'
        assert response['sources'][0]['status']=='success'
        assert response['sources'][0]['fetched']==1
        assert response['count']==1
        saved=next(job for job in client.get('/api/v1/applications').json() if job['job_url']=='https://jobs.ashbyhq.com/example/123')
        assert saved['source']=='Context.dev web search'
        assert saved['match_score']>=0
