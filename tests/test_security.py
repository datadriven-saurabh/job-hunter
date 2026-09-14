import asyncio
import httpx
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.security import LocalSecurityMiddleware
from backend.agents import job_sources


def test_origins_cache_and_host_boundary(monkeypatch):
    monkeypatch.delenv('TRUSTED_EXTENSION_IDS', raising=False)
    with TestClient(app) as client:
        for origin in ['https://evil.example', 'null', 'chrome-extension://'+'a'*32, 'chrome-extension://fake']:
            assert client.get('/api/v1/profile', headers={'Origin': origin}).status_code == 403
            assert client.post('/api/v1/demo', headers={'Origin': origin}).status_code == 403
        assert client.get('/api/v1/profile',headers={'Sec-Fetch-Site':'cross-site'}).status_code == 403
        assert client.get('/health',headers={'Host':'evil.example'}).status_code == 400
        assert client.get('/api/v1/profile').json() is None
        result=client.get('/api/v1/profile',headers={'Origin':'http://localhost:3000'})
        assert result.headers['cache-control']=='no-store'
        assert result.headers['x-content-type-options']=='nosniff'
        assert result.headers['access-control-allow-origin']=='http://localhost:3000'
        monkeypatch.setenv('TRUSTED_EXTENSION_IDS','a'*32)
        allowed='chrome-extension://'+'a'*32
        assert client.get('/api/v1/profile',headers={'Origin':allowed}).status_code == 200
        preflight=client.options('/api/v1/profile',headers={'Origin':allowed,'Access-Control-Request-Method':'GET'})
        assert preflight.status_code==200
        assert preflight.headers['access-control-allow-origin']==allowed
        assert client.get('/api/v1/profile',headers={'Origin':'chrome-extension://'+'b'*32}).status_code==403


def test_request_size_limit_before_parsing():
    with TestClient(app) as client:
        assert client.post('/api/v1/profile',content=b'x',headers={'Content-Length':'2000000'}).status_code==413
        assert client.post('/api/v1/resumes/upload',content=b'x',headers={'Content-Length':'12000000'}).status_code==413
    async def chunked():
        called=[];sent=[]
        async def downstream(scope,receive,send):called.append(True)
        parts=iter([{'type':'http.request','body':b'x'*600000,'more_body':True}]*2)
        async def receive():return next(parts)
        async def send(message):sent.append(message)
        await LocalSecurityMiddleware(downstream)({'type':'http','headers':[],'path':'/api/v1/profile','method':'POST'},receive,send)
        assert not called and sent[0]['status']==413
    asyncio.run(chunked())


def test_public_redirects_and_limits(monkeypatch):
    real_client=httpx.Client
    seen=[]
    def transport(request):
        seen.append(str(request.url))
        return httpx.Response(302,headers={'Location':'http://127.0.0.1:8000/api/v1/profile'})
    monkeypatch.setattr(job_sources.httpx,'Client',lambda **kw:real_client(transport=httpx.MockTransport(transport),**kw))
    with pytest.raises(job_sources.SourceUnavailable):job_sources.public_get('https://www.linkedin.com/jobs/view/123')
    assert len(seen)==1
    for url in ['https://user:pass@www.linkedin.com/jobs/1','https://www.linkedin.com:8443/jobs/1','https://www.linkedin.com:notaport/jobs/1']:
        with pytest.raises(job_sources.SourceUnavailable):job_sources.public_get(url)
    assert len(seen)==1
    monkeypatch.setattr(job_sources.httpx,'Client',lambda **kw:real_client(transport=httpx.MockTransport(lambda r:httpx.Response(200,content=b'x'*(12*1024*1024+1))),**kw))
    with pytest.raises(job_sources.SourceUnavailable,match='12 MB'):job_sources.public_get('https://www.linkedin.com/jobs/view/123')


def test_local_ai_does_not_use_environment_proxy(monkeypatch):
    from backend.agents import llm
    from backend.demo import CONFIG
    monkeypatch.setenv('ENABLE_LOCAL_LLM','true')
    calls=[]
    def post(url,**kwargs):
        calls.append(kwargs)
        return httpx.Response(200,json={'response':'{}'},request=httpx.Request('POST',url))
    monkeypatch.setattr(llm.httpx,'post',post)
    assert llm.generate_json('synthetic facts',CONFIG)=={}
    assert calls[0]['trust_env'] is False
