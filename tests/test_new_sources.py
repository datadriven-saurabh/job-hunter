"""Public-board fixtures use synthetic employers and no account credentials."""
import json
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.agents import job_sources
from backend.agents.public_boards import BOARDS, public_page_jobs, jobfluent_posting, workingnomads_jobs


@pytest.mark.parametrize('provider,path',[
 ('relocate','/germany/berlin/example/data-analyst-123'),
 ('berlinstartupjobs','/engineering/data-analyst-example/'),
 ('eustartups','/job/data-analyst-example/'),
 ('hvcapital','/companies/example/jobs/123-data-analyst'),
 ('earlybird','/companies/example/jobs/123-data-analyst'),
 ('pointnine','/companies/example/jobs/123-data-analyst'),
])
def test_new_boards_prioritize_relevant_links_and_preserve_metadata(monkeypatch,provider,path):
    from urllib.parse import urlparse
    base=BOARDS[provider][1];url='https://'+urlparse(base).netloc+path
    irrelevant=url.replace('data-analyst','accountant')
    payload={'@type':'JobPosting','title':'Data Analyst','hiringOrganization':{'name':'Example'},
             'description':'Analyze SQL data and build reporting dashboards. '*10,'datePosted':'2026-09-14',
             'identifier':{'value':'REQ-42'},'employmentType':['FULL_TIME'],'jobLocationType':'TELECOMMUTE'}
    calls=[]
    class Response:
        def __init__(self,text,url):self.text=text;self.url=url
    def fetch(target):
        calls.append(target)
        if target==base:return Response(f'<a href="{irrelevant}">Accountant</a><a href="{url}#content">Data Analyst</a><a href="https://private.example/jobs/fake">Data Analyst</a>',base)
        assert target==url
        return Response('<script type="application/ld+json">'+json.dumps(payload)+'</script>',target)
    monkeypatch.setattr(job_sources,'public_get',fetch)
    jobs=public_page_jobs(provider,keywords='Data Analyst',limit=1)
    assert len(jobs)==1 and calls==[base,url]
    assert jobs[0]['job_url']==url and jobs[0]['source_url']==url
    assert jobs[0]['posted_at']=='2026-09-14' and jobs[0]['requisition_id']=='REQ-42'
    assert jobs[0]['employment_type']=='Full-time' and not jobs[0]['description_incomplete']


def test_jobfluent_microdata_uses_employer_not_site_name():
    text='''<meta itemprop="name" content="JobFluent"><article itemtype="https://schema.org/JobPosting">
    <meta itemprop="datePosted" content="2026-09-14"><span itemprop="title">Data Analyst</span>
    <span itemprop="hiringOrganization"><span itemprop="name">Example Corp</span></span>
    <span itemprop="jobLocation"><span itemprop="addressLocality">Berlin</span></span>
    <div class="hide-desc-true"><div itemprop="description">SQL analytics description preview.</div></div></article>'''
    job=jobfluent_posting(text,'https://www.jobfluent.com/jobs/example?result=5')[0]
    assert job['company_name']=='Example Corp' and job['posted_at']=='2026-09-14'
    assert job['description_incomplete'] and '?' not in job['job_url']


def test_workingnomads_filters_and_caches_full_feed(monkeypatch):
    calls=[]
    class Response:
        def json(self):return [{'url':'https://www.workingnomads.com/job/go/42/','title':'Data Analyst','company_name':'Example','description':'SQL analytics','location':'Europe','pub_date':'2026-09-14T14:00:00Z'}, {'url':'http://127.0.0.1/job','title':'Data Analyst','company_name':'Unsafe','description':'SQL'}]
    monkeypatch.setattr(job_sources,'public_get',lambda url:calls.append(url) or Response())
    assert workingnomads_jobs('SQL')[0]['posted_at']=='2026-09-14T14:00:00Z'
    assert workingnomads_jobs('Python')==[]
    assert len(workingnomads_jobs())==1 and len(calls)==1


def test_access_block_suspends_entire_source_across_queries(monkeypatch):
    calls=[]
    def blocked(*args,**kwargs):calls.append(args);raise job_sources.SourceUnavailable('Public access unavailable (HTTP 403).')
    monkeypatch.setattr(job_sources,'retrieve',blocked)
    assert 'wellfound' in {s['id'] for s in job_sources.source_catalog()}
    for query in ['Data Analyst','Business Analyst']:
        with pytest.raises(job_sources.SourceUnavailable,match='403'):job_sources.discover('wellfound',keywords=query)
    assert len(calls)==1
    assert 'wellfound' not in {s['id'] for s in job_sources.source_catalog()}
    assert not next(s for s in job_sources.source_catalog(True) if s['id']=='wellfound')['available']
    with TestClient(app) as c:
        assert 'startupjobs' not in {s['id'] for s in c.get('/api/v1/jobs/sources').json()}
        assert 'startupjobs' in {s['id'] for s in c.get('/api/v1/jobs/sources?include_unavailable=true').json()}


def test_literal_newlines_in_public_jsonld_do_not_drop_job():
    jobs=job_sources.jsonld_jobs('<script type="application/ld+json">{"@type":"JobPosting","title":"Data Analyst","description":"SQL\nanalytics","hiringOrganization":{"name":"Example"}}</script>')
    assert len(jobs)==1 and 'SQL' in jobs[0]['description']


def test_country_aliases_do_not_discard_german_jobs_or_match_substrings():
    from backend.services.job_matching import location_matches
    assert location_matches('Berlin, DE','Germany')
    assert location_matches('Berlin, Deutschland','Germany')
    assert location_matches('Berlin, Germany','Europe')
    assert location_matches('Amsterdam, NL','European Union')
    assert not location_matches('Seoul, South Korea','EU')
    assert not location_matches('London, UK','EU')
    assert location_matches('London, UK','Europe')
    assert not location_matches('Berlin, New Hampshire, USA','Germany')
