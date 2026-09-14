import asyncio
import json
import os
from datetime import datetime, timezone
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from backend import database as db
from backend.agents.tailor_agent import tailor

lock=asyncio.Lock()
MAPPINGS={'email':['input[type="email"]','input[name="email"]'], 'first_name':['input[name="first_name"]','input[name="firstName"]'], 'last_name':['input[name="last_name"]','input[name="lastName"]'], 'full_name':['input[name="name"]'], 'phone':['input[type="tel"]']}

def fields(profile):
    p=profile['personal_details']; parts=p['full_name'].split(' ',1)
    return {'first_name':parts[0],'last_name':parts[1] if len(parts)>1 else '', 'full_name':p['full_name'],'email':p['email'],'phone':p['phone'],'linkedin_url':p.get('linkedin_url'),'github_url':p.get('github_url')}

def log(job_id,result,action,error=None):
    job=db.get_job(job_id)
    logs=job['submission_logs']+[{'timestamp':datetime.now(timezone.utc).isoformat(),'action':action,'result':result,'error_message':error}]
    db.execute('UPDATE application_records SET submission_logs_json=:logs, updated_at=CURRENT_TIMESTAMP WHERE job_id=:id',{'id':job_id,'logs':json.dumps(logs)})

async def run_batch(ids, submit=False):
    async with lock:
        for job_id in ids:
            job=db.get_job(job_id)
            if not job or job['status']!='QUEUED': continue
            try:
                profile=db.profile(job['user_id']); config=db.config(job['user_id'])
                if submit:
                    resume,cover=job['tailored_resume_path'],job['tailored_cover_letter_path']
                else:
                    resume,cover=await asyncio.to_thread(tailor,job,profile)
                db.execute("UPDATE application_records SET status='TAILORED',tailored_resume_path=:resume,tailored_cover_letter_path=:cover WHERE job_id=:id",{'id':job_id,'resume':resume,'cover':cover})
                log(job_id,'SUCCESS','Using reviewed documents' if submit else 'Prepared documents from the selected resume')
                if not submit or job.get('demo') or os.getenv('ENABLE_LIVE_SUBMISSION')!='true' or not config['execution_preferences']['enable_headless_auto_apply'] or job['classification']!='HEADLESS_AUTO':
                    log(job_id,'NEEDS_HUMAN','Documents ready for review; use the application link and extension')
                    continue
                count=db.query("SELECT COUNT(*) AS n FROM application_records WHERE status='APPLIED' AND date(updated_at)=date('now')")[0]['n']
                if count>=config['execution_preferences']['max_daily_applications']:
                    log(job_id,'NEEDS_HUMAN','Daily application limit reached'); continue
                async with async_playwright() as p:
                    browser=await p.chromium.launch(headless=True)
                    try:
                        page=await browser.new_page(service_workers="block")
                        allowed={'jobs.lever.co','api.lever.co','boards.greenhouse.io','job-boards.greenhouse.io','boards-api.greenhouse.io'}
                        async def guard(route):
                            parsed=urlparse(route.request.url)
                            if parsed.scheme!='https' or parsed.hostname not in allowed or parsed.username or parsed.port not in {None,443}: await route.abort()
                            else: await route.continue_()
                        await page.route('**/*',guard)
                        await page.goto(job['job_url'],wait_until='domcontentloaded',timeout=30000)
                        if await page.locator('iframe[src*="captcha"],input[type="password"],iframe[src*="challenges.cloudflare"]').count():
                            log(job_id,'NEEDS_HUMAN','Authentication or CAPTCHA requires browser assistance');continue
                        outcome=await fill_and_submit(page,fields(profile),resume)
                        if outcome!='SUCCESS':
                            log(job_id,'NEEDS_HUMAN',outcome);continue
                        db.execute("UPDATE application_records SET status='APPLIED',updated_at=CURRENT_TIMESTAMP WHERE job_id=:id",{'id':job_id})
                        log(job_id,'SUCCESS','Application submission confirmed by portal')
                    finally: await browser.close()
            except Exception as exc:
                # A failed job remains retryable, without claiming a submission occurred.
                db.execute("UPDATE application_records SET status=CASE WHEN tailored_resume_path IS NULL THEN 'MATCHED' ELSE 'TAILORED' END WHERE job_id=:id",{'id':job_id})
                log(job_id,'FAILED','Application preparation or execution failed',str(exc)[:400])

import re


async def fill_and_submit(page, data, resume):
    """Shared execution path, also exercised against a local-only test form."""
    for key,selectors in MAPPINGS.items():
        for selector in selectors:
            inputs=page.locator(selector)
            if await inputs.count() and data.get(key):
                input=inputs.first
                if await input.is_visible() and await input.is_editable():
                    await input.fill(data[key]);break
    uploads=page.locator('input[type="file"]')
    if await uploads.count(): await uploads.first.set_input_files(resume)
    # Do not guess answers or agree to terms on the candidate's behalf.
    if await page.locator('input:invalid,select:invalid,textarea:invalid').count():
        return 'Required answers remain. Complete this application in your browser.'
    submit=page.get_by_role('button',name='Submit application',exact=False)
    if await submit.count()!=1:
        return 'Could not identify a unique submission button'
    await submit.click()
    try: await page.get_by_text(re.compile(r'thank you for applying|application (has been )?(received|submitted)',re.I)).first.wait_for(timeout=10000)
    except Exception:
        return 'Submission outcome unconfirmed. Review before retrying.'
    return 'SUCCESS'
