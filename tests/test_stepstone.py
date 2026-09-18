import json
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.agents import job_sources as source
from backend.services.job_intelligence import enrich
from backend.services.posting_language import posting_language


def test_posting_language_is_separate_and_conservative():
    english='We are looking for an experienced analyst to work with our team and build reports for your stakeholders. The role will include requirements and responsibilities.'
    german='Wir suchen einen Analysten für unser Team. Du arbeitest mit deinen Kenntnissen und deiner Erfahrung an den Aufgaben für die Stelle und das Unternehmen.'
    assert posting_language(english)['label']=='English'
    assert posting_language(german)['label']=='German'
    assert posting_language('SQL Python')['label']=='Unknown'
    assert posting_language('',explicit='de-DE')=={'label':'German','method':'Source supplied','confidence':'source'}

URL='https://www.stepstone.de/stellenangebote--Data-Analyst-Berlin-Example--123456-inline.html'
JOB={'@type':'JobPosting','title':'Data Analyst','hiringOrganization':{'name':'Example'},'description':'SQL analytics and dashboards for a product team. We provide visa sponsorship.','url':URL,'datePosted':'2025-09-01T10:30:00Z','identifier':{'value':'REQ-123'},'jobLocation':{'address':{'addressLocality':'Berlin'}}}
def markup(job):return '<script type="application/ld+json">'+json.dumps(job)+'</script>'
class Response:
    def __init__(self,text):self.text=text


def test_structured_stepstone_metadata(monkeypatch):
    calls=[]
    monkeypatch.setattr(source,'public_get',lambda url:(calls.append(url) or Response(markup(JOB))))
    rows=source.retrieve('stepstone',keywords='Data Analyst',location='Berlin')
    assert calls==['https://www.stepstone.de/jobs/data-analyst/in-berlin']
    assert len(rows)==1
    job=enrich(rows[0]);assert job['source']=='StepStone' and job['requisition_id']=='REQ-123'
    assert job['posted_at']=='2025-09-01T10:30:00+00:00' and job['visa_status']=='explicit_yes'


def test_stepstone_bounded_detail_links_and_host_validation(monkeypatch):
    calls=[]
    def get(url):
        calls.append(url)
        if '/jobs/' in url:return Response(f'<a href="{URL}">Role</a><a href="{URL}">Duplicate</a><a href="https://www.stepstone.de.evil.test/stellenangebote--bad--123-inline.html">Bad</a>')
        return Response(markup(JOB))
    monkeypatch.setattr(source,'public_get',get)
    assert len(source.retrieve('stepstone',keywords='Data Analyst',limit=1))==1
    assert len(calls)==2 and calls[-1]==URL


def test_stepstone_blocks_reported_not_empty_success(monkeypatch):
    def denied(*a,**k):raise source.SourceUnavailable('Public access unavailable (HTTP 403).')
    monkeypatch.setattr(source,'public_get',denied)
    with TestClient(app) as c:
        c.post('/api/v1/demo')
        response=c.post('/api/v1/jobs/search',json={'provider':'stepstone','keywords':'Data Analyst','location':'Berlin'}).json()
        assert response['sources'][0]['status']=='unavailable'
        assert '403' in response['sources'][0]['message']
        assert not any(s['id']=='stepstone' for s in c.get('/api/v1/jobs/sources').json())
        assert any(s['id']=='stepstone' and not s['available'] for s in c.get('/api/v1/jobs/sources?include_unavailable=true').json())


def test_stepstone_empty_markup_is_unavailable(monkeypatch):
    monkeypatch.setattr(source,'public_get',lambda url:Response('<html>Sign in</html>'))
    with pytest.raises(source.SourceUnavailable):source.retrieve('stepstone',keywords='Analyst')
