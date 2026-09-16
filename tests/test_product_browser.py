"""Opt-in browser audit against production UI + isolated FastAPI server.

No live API data or employer pages are used. Run after building frontend.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import time
from urllib.parse import urlparse
import httpx
import pytest
import threading
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from backend import security
from playwright.sync_api import sync_playwright, expect
from backend.main import app
from backend import database as db

pytestmark=pytest.mark.skipif(os.environ.get('RUN_BROWSER_TESTS')!='1',reason='Opt-in isolated browser audit')
ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def browser_app(tmp_path,monkeypatch):
    if not (ROOT/'frontend/.next/BUILD_ID').exists():pytest.fail('Build frontend before browser tests.')
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    origin=f'http://127.0.0.1:{port}'
    from backend import model_api
    monkeypatch.setattr(model_api,'tags',lambda:[{'name':n,'size':1000} for n in ['qwen3:4b','qwen2.5:1.5b','nomic-embed-text:latest']])
    log=(tmp_path/'web.log').open('w')
    process=subprocess.Popen(['node',str(ROOT/'frontend/node_modules/next/dist/bin/next'),'start','--hostname','127.0.0.1','--port',str(port)],cwd=ROOT/'frontend',stdout=log,stderr=log,env={**os.environ,'NEXT_TELEMETRY_DISABLED':'1'})
    try:
        for _ in range(80):
            try:
                if httpx.get(origin,timeout=.5,trust_env=False).status_code==200:break
            except httpx.HTTPError:pass
            time.sleep(.1)
        else:pytest.fail('Test frontend did not start')
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));api_port=sock.getsockname()[1]
        api_origin=f'http://127.0.0.1:{api_port}'
        # Only this isolated fixture accepts its random frontend origin.
        monkeypatch.setattr(security,'WEB_ORIGINS',security.WEB_ORIGINS|{origin})
        test_app=CORSMiddleware(app,allow_origins=[origin],allow_methods=['*'],allow_headers=['*'])
        server=uvicorn.Server(uvicorn.Config(test_app,host='127.0.0.1',port=api_port,log_level='error',access_log=False))
        thread=threading.Thread(target=server.run,daemon=True);thread.start()
        for _ in range(100):
            if server.started:break
            time.sleep(.05)
        assert server.started
        with httpx.Client(base_url=api_origin,trust_env=False,timeout=30) as client,sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True)
            context=browser.new_context(viewport={'width':1440,'height':1000},service_workers='block')
            errors=[];page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            def route_request(route):
                request=route.request;url=urlparse(request.url)
                if url.hostname in {'localhost','127.0.0.1'} and url.port==8000:
                    path=url.path+('?' + url.query if url.query else '')
                    route.continue_(url=api_origin+path)
                elif request.url.startswith(origin+'/') or request.url==origin:route.continue_()
                else:route.abort()
            context.route('**/*',route_request)
            page.goto(origin);expect(page.get_by_text('Local engine connected',exact=True)).to_be_visible()
            try:
                yield page,client,errors
            finally:
                print('Browser errors:',errors)
                page.screenshot(path=str(tmp_path/'last-ui.png'),full_page=True)
                browser.close()
    finally:
        if 'server' in locals():
            server.should_exit=True;thread.join(timeout=10)
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait()
        log.close()


def test_core_user_journey(browser_app,tmp_path):
    page,client,errors=browser_app
    page.get_by_role('button',name='Explore demo workspace').click()
    expect(page.locator('tbody tr')).to_have_count(6)
    jobs=client.get('/api/v1/applications').json();job=jobs[0]
    page.get_by_role('button',name='My profile',exact=True).click()
    expect(page.locator('input[type="month"]')).to_have_count(4)
    page.get_by_label('Public resume / portfolio URL').fill('https://portfolio.example/resume')
    page.get_by_role('button',name='Save profile',exact=True).click()
    expect(page.get_by_role('dialog')).to_have_count(0)
    assert client.get('/api/v1/profile').json()['personal_details']['portfolio_url']=='https://portfolio.example/resume'
    page.get_by_role('button',name='My documents',exact=True).click()
    resume=tmp_path/'analytics.txt';resume.write_text('Synthetic Analyst\nPython SQL dashboards Power BI Tableau. Built reliable business analytics reporting for stakeholders.')
    page.get_by_label('Upload resume files').set_input_files(str(resume))
    expect(page.get_by_text('1 resume file processed and indexed locally.',exact=True)).to_be_visible()
    page.get_by_role('button',name='Discover jobs',exact=True).click()
    page.get_by_role('button',name='View '+job['company_name']+' opportunity',exact=True).click()
    page.get_by_role('button',name='Prepare application',exact=True).click()
    expect(page.get_by_text('Prepare from verified facts.',exact=True)).to_be_visible()
    expect(page.get_by_role('dialog').locator('select option')).to_have_count(1)
    page.get_by_role('button',name='Prepare 1 application',exact=True).click()
    expect(page.get_by_role('dialog')).to_have_count(0)
    for _ in range(100):
        if db.get_job(job['job_id'])['status']=='TAILORED':break
        time.sleep(.05)
    assert db.get_job(job['job_id'])['status']=='TAILORED'
    assert client.get(f"/api/v1/applications/{job['job_id']}/document/resume").content.startswith(b'%PDF')
    page.get_by_role('button',name='Application studio',exact=True).click()
    page.get_by_label('Saved job',exact=True).select_option(job['job_id'])
    page.get_by_label('Employer Job ID / requisition number').fill('QA-123')
    page.get_by_label('Public resume or portfolio URL',exact=True).fill('https://portfolio.example/cv')
    page.get_by_role('button',name='Create validated application kit').click()
    expect(page.get_by_role('link',name='Download ATS Markdown')).to_be_visible(timeout=30000)
    note=page.get_by_label('Connection note · fewer than 300 characters')
    note.fill(note.input_value().replace('Hi there','Hello there'))
    expect(page.get_by_text('Unsaved edits.',exact=False)).to_be_visible()
    expect(page.get_by_role('link',name='Download saved text',exact=True)).to_have_count(0)
    page.get_by_role('button',name='Validate and save edited drafts').click()
    expect(page.get_by_text('Format checked · review changed facts',exact=True)).to_be_visible()
    page.get_by_text('Answer application questions',exact=True).click()
    page.get_by_label('Questions',exact=True).fill('Tell me about a time you improved a process.')
    page.get_by_role('button',name='Draft answers',exact=True).click()
    expect(page.get_by_role('heading',name='Tell me about a time you improved a process.',exact=True)).to_be_visible()
    page.get_by_role('button',name='Interview coach',exact=True).click()
    page.get_by_label('Practice for',exact=True).select_option(job['job_id'])
    page.get_by_role('button',name='Start practice',exact=True).click()
    page.get_by_label('Your answer',exact=True).fill('At the time my task was to improve speed. I built a cache and reduced latency by 30%.')
    page.get_by_role('button',name='Get feedback',exact=False).click()
    expect(page.get_by_text('Rubric coverage',exact=False)).to_be_visible()
    page.get_by_role('button',name='Discover jobs',exact=True).click()
    page.get_by_label('Sort opportunities by').select_option('company')
    page.get_by_label('Sort direction').select_option('asc')
    page.get_by_role('button',name='Delete '+job['company_name']+' opportunity',exact=True).click()
    expect(page.locator('tbody tr')).to_have_count(7)
    page.get_by_text('Deleted opportunities',exact=False).first.click()
    page.get_by_role('button',name='Restore '+job['company_name'],exact=True).click()
    expect(page.locator('tbody tr')).to_have_count(8)
    page.get_by_role('button',name='Find opportunities',exact=False).first.click()
    page.get_by_role('button',name='Select all public boards',exact=True).click()
    from backend.agents.job_sources import source_catalog
    expect(page.locator('.source-checkboxes input:checked')).to_have_count(sum(s['kind']!='company-board' for s in source_catalog()))
    expect(page.locator('.source-checkboxes')).not_to_contain_text('StepStone')
    page.get_by_role('button',name='Close dialog',exact=True).click()
    page.get_by_role('button',name='Model lab',exact=True).click()
    expect(page.get_by_role('button',name='Run evidence benchmark',exact=True)).to_be_disabled()
    page.get_by_text('Task-specific model routing',exact=True).click()
    page.get_by_role('button',name='Save routing',exact=True).click()
    expect(page.get_by_label('embedding',exact=True)).to_have_value('nomic-embed-text:latest')
    page.screenshot(path=str(tmp_path/'dashboard.png'),full_page=True)
    assert errors==[]


def test_more_than_one_hundred_opportunities_accessible(browser_app):
    page,client,errors=browser_app
    client.post('/api/v1/demo');job=client.get('/api/v1/applications').json()[0]
    with db.engine.begin() as conn:
        for i in range(105):
            conn.execute(db.text("INSERT INTO application_records(job_id,user_id,company_name,job_title,job_url,match_score,classification,status) VALUES (:id,'local',:company,'Analyst',:url,0.1,'HUMAN_IN_THE_LOOP_LINK','MATCHED')"),{'id':f'paging-{i}','company':f'Test {i:03d}','url':f'https://example.com/jobs/{i}'})
    page.reload();page.get_by_role('button',name='Discover jobs',exact=True).click()
    expect(page.locator('tbody tr')).to_have_count(100)
    page.get_by_role('button',name='Next page',exact=True).click()
    expect(page.locator('tbody tr')).to_have_count(13)
    page.get_by_label('Select all visible opportunities').check()
    expect(page.get_by_text('13 opportunities selected',exact=True)).to_be_visible()
    page.get_by_role('button',name='Previous page',exact=True).click()
    expect(page.locator('tbody tr')).to_have_count(100)
    assert errors==[]
