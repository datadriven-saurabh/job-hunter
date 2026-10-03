"""Run against a hosted test build (auth.example.test); all auth responses are synthetic."""
import json, os, re, socket, subprocess, sys, time
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright, expect
root=Path(sys.argv[1]).resolve()
with socket.socket() as sock:
 sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
origin=f'http://127.0.0.1:{port}'
user={'id':'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee','aud':'authenticated','role':'authenticated','email':'test@example.test','email_confirmed_at':'2026-01-01T00:00:00Z','app_metadata':{'provider':'email'},'user_metadata':{},'created_at':'2026-01-01T00:00:00Z'}
session={'access_token':'synthetic-access-token','refresh_token':'synthetic-refresh-token','token_type':'bearer','expires_in':3600,'expires_at':int(time.time())+3600,'user':user}
process=subprocess.Popen(['node',str(root/'node_modules/next/dist/bin/next'),'start','--hostname','127.0.0.1','--port',str(port)],cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
 for _ in range(80):
  try:
   if httpx.get(origin,timeout=.5).status_code==200:break
  except httpx.HTTPError:pass
  time.sleep(.1)
 with sync_playwright() as pw:
  browser=pw.chromium.launch()
  def context():
   ctx=browser.new_context();calls=[]
   def auth(route):
    calls.append((route.request.url,route.request.post_data_json if route.request.post_data else None))
    if '/user' in route.request.url:body=user
    elif '/resend' in route.request.url:body={}
    else:body=session
    route.fulfill(status=200,content_type='application/json',body=json.dumps(body))
   ctx.route('https://auth.example.test/**',auth)
   ctx.route('http://localhost:8000/**',lambda r:r.fulfill(status=200,content_type='application/json',body='[]' if '/applications' in r.request.url or '/resumes' in r.request.url else 'null'))
   return ctx,calls
  for path in ['/dashboard','/','/login']:
   ctx,calls=context();page=ctx.new_page()
   page.goto(origin+path+'#access_token=synthetic-access-token&refresh_token=synthetic-refresh-token&token_type=bearer&expires_in=3600&type=signup')
   page.wait_for_url(re.compile(r'/dashboard#?$'));page.wait_for_function("Object.keys(localStorage).some(k=>k.endsWith('-auth-token'))")
   assert 'access_token' not in page.url
   page.reload();page.wait_for_timeout(400)
   assert page.url.rstrip('#')==origin+'/dashboard'
   # A later visit to login recognises the persisted verified session.
   page.goto(origin+'/login');page.wait_for_url(re.compile(r'/dashboard#?$'))
   ctx.close()
  ctx,calls=context();page=ctx.new_page()
  page.goto(origin+'/dashboard#error=access_denied&error_code=otp_expired&error_description=sensitive-provider-text')
  expect(page.locator('p[role=alert]')).to_contain_text('expired or was already used')
  assert 'sensitive-provider-text' not in page.url
  page.get_by_label('Email',exact=True).fill('test@example.test')
  page.get_by_role('button',name='Resend confirmation email').click()
  expect(page.get_by_role('status')).to_contain_text('new confirmation email')
  resend=next(data for url,data in calls if '/resend' in url)
  assert resend['email']=='test@example.test'
  assert any('redirect_to=' in url and '/resend' in url for url,data in calls)
  page.get_by_label('Password',exact=True).fill('synthetic-password')
  page.get_by_role('button',name='Sign in',exact=True).click()
  page.wait_for_url(re.compile(r'/dashboard#?$'))
  assert any('grant_type=password' in url for url,data in calls)
  ctx.close();browser.close()
 print('PASS: callback auto-login at dashboard/root/login, session persistence, expired-link recovery, resend, and password login')
finally:
 process.terminate();process.wait(timeout=10)
