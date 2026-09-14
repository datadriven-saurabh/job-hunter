import io
from fastapi.testclient import TestClient
from pypdf import PdfReader
from backend.main import app
from backend import database as db
from backend.services.outreach import drafts
from backend.demo import PROFILE

JOB={'job_title':'Software Engineer','company_name':'Example Company','job_url':'https://jobs.lever.co/example/123','description':'Build accessible software using TypeScript, React and Python. Work with our product and design teams to deliver reliable user experiences. Your personal contact for this position is Jane Smith.'}

def test_kit_pdf_messages_and_edits():
    with TestClient(app) as c:
        c.post('/api/v1/demo')
        result=c.post('/api/v1/studio/kits',json=JOB)
        assert result.status_code==200,result.text
        kit=result.json();id=kit['id']
        pdf=c.get(f'/api/v1/studio/kits/{id}/resume')
        reader=PdfReader(io.BytesIO(pdf.content));assert len(reader.pages)==1
        text=reader.pages[0].extract_text()
        assert PROFILE['personal_details']['full_name'].upper() in text
        assert 'CHLOE' not in text and 'Summary' in text and 'Education' in text
        assert len(kit['connection_note'])<=200 and JOB['job_url'] in kit['referral_message']
        assert kit['named_contacts'][0]['name']=='Jane Smith'
        assert 'not necessarily' in kit['contact_note']
        kit['cover_letter']='Reviewed letter with my own edits.'
        assert c.patch(f'/api/v1/studio/kits/{id}',json=kit).status_code==200
        assert c.get(f'/api/v1/studio/kits/{id}/cover_letter').text==kit['cover_letter']
        assert len(c.get('/api/v1/studio/kits').json())==1
        kit['connection_note']='x'*201
        assert c.patch(f'/api/v1/studio/kits/{id}',json=kit).status_code==422
        assert c.post('/api/v1/studio/kits',json={}).status_code==400


def test_link_reader_blocks_private_and_unsupported_hosts(monkeypatch):
    import backend.studio_api as studio
    calls=[]
    monkeypatch.setattr(studio,'public_get',lambda url:calls.append(url))
    with TestClient(app) as c:
        for url in ['http://127.0.0.1:8000','https://localhost/private','https://jobs.lever.co.evil.test/job','https://user:pass@jobs.lever.co/job']:
            assert c.post('/api/v1/studio/resolve',json={'url':url}).status_code==400
        assert not calls


def test_structured_job_link(monkeypatch):
    import backend.studio_api as studio
    class R:text='<script type="application/ld+json">{"@type":"JobPosting","title":"Data Analyst","hiringOrganization":{"name":"Example"},"url":"https://jobs.lever.co/example/1","description":"SQL dashboards for customers"}</script>'
    monkeypatch.setattr(studio,'public_get',lambda url:R())
    with TestClient(app) as c:
        result=c.post('/api/v1/studio/resolve',json={'url':'https://jobs.lever.co/example/1'}).json()
        assert result['company_name']=='Example' and result['review_required']


def test_model_comparison_is_measured_and_local(monkeypatch):
    import backend.model_api as models
    monkeypatch.setattr(models,'tags',lambda:[{'name':'test-model'}])
    monkeypatch.setattr(models,'generate_json',lambda *a,**k:{'matched':['SQL','Python'],'missing':['dbt']})
    with TestClient(app) as c:
        c.post('/api/v1/demo')
        assert c.post('/api/v1/models/active',json={'name':'absent'}).status_code==400
        assert c.post('/api/v1/models/active',json={'name':'test-model'}).status_code==200
        assert c.post('/api/v1/models/compare',json={'models':['test-model']}).status_code==200
        result=c.get('/api/v1/models/comparison').json()
        assert result['status']=='complete' and result['results'][0]['passed']==1


def test_new_job_source_adapters(monkeypatch):
    from backend.agents import job_sources as source
    class Response:
        def __init__(self,data):self.data=data
        def json(self):return self.data
    def fetch(url,params=None):
        if 'arbeitnow' in url:return Response({'data':[{'title':'Data Analyst','company_name':'Example','url':'https://www.arbeitnow.com/jobs/example','description':'SQL analytics','remote':True,'location':'Berlin'}]})
        if url.endswith('/postings'):return Response({'totalFound':1,'content':[{'id':'123','name':'Data Analyst'}]})
        return Response({'name':'Data Analyst','company':{'name':'Example'},'location':{'city':'Berlin'},'jobAd':{'sections':{'jobDescription':{'text':'SQL analytics'}}}})
    monkeypatch.setattr(source,'public_get',fetch)
    for provider in ['arbeitnow','arbeitnow_uk','smartrecruiters']:
        result=source.retrieve(provider,board='Example',keywords='Data Analyst')
        assert len(result)==1 and 'SQL' in result[0]['description'] and result[0]['source_url'].startswith('https://')
