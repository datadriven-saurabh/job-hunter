import os
# Newly written profiles, documents and caches should be private to the OS user.
if os.name == "posix": os.umask(0o077)
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
# This local edition must not inherit opt-in cloud tracing from another project.
os.environ['LANGCHAIN_TRACING_V2'] = 'false'
os.environ['LANGCHAIN_TRACING'] = 'false'
os.environ['LANGSMITH_TRACING'] = 'false'
import json
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from backend.state import queue_reservation, profile_write
from pydantic import BaseModel, Field
from schemas import UserProfile, SystemVariables, ApplicationStatus, InterviewQuestion, UserAnswerFeedback
from backend import database as db
from backend.agents.orchestrator import discovery_graph
from backend.agents.scout_agent import fetch_feed
from backend.agents.apply_agent import run_batch, fields, log
from backend.agents.coach_agent import questions, feedback
from backend import demo
from backend.resume_api import router as resume_router
from backend.services import resumes
from backend.agents.job_sources import SOURCE_INFO, source_catalog, discover as discover_source

@asynccontextmanager
async def lifespan(app):
    db.init_db()
    from backend.services import studio_store
    import shutil
    studio_store.migrate_kits()
    shutil.rmtree(db.DATA/'kits'/'.pending',ignore_errors=True)
    db.execute("UPDATE studio_runs SET state='failed',error='Preparation was interrupted by a restart. Retry from Application Studio.' WHERE state IN ('queued','running')")
    # Keep reviewed documents and any unconfirmed submission log after a restart.
    db.execute("UPDATE application_records SET status=CASE WHEN tailored_resume_path IS NOT NULL THEN 'TAILORED' WHEN job_id IN (SELECT job_id FROM studio_runs UNION SELECT job_id FROM studio_kits WHERE job_id IS NOT NULL) THEN 'REVIEWING' ELSE 'MATCHED' END WHERE status='QUEUED'")
    app.state.chromium_path = ''
    async def probe_browser():
        from playwright.async_api import async_playwright
        async with async_playwright() as pw:
            return pw.chromium.executable_path
    try:
        app.state.chromium_path = await asyncio.wait_for(probe_browser(), timeout=10)
    except Exception:
        pass  # Browser setup must not prevent discovery or document preparation.
    yield

app=FastAPI(title='Job Hunter Orchestrator API',version='1.0.0',lifespan=lifespan)
app.include_router(resume_router)
from backend.studio_api import router as studio_router
app.include_router(studio_router)
from backend.model_api import router as model_router
app.include_router(model_router)
from backend.career_api import router as career_router
app.include_router(career_router)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['localhost','127.0.0.1','testserver'])
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:3000','http://127.0.0.1:3000'],allow_credentials=False,allow_methods=['GET','POST','PATCH','PUT','DELETE'],allow_headers=['Content-Type','If-Match'])

from backend.security import LocalSecurityMiddleware
app.add_middleware(LocalSecurityMiddleware)

def require_job(id):
    job=db.get_job(id)
    if not job: raise HTTPException(404,'Application not found')
    return job

def require_profile(id='local'):
    value=db.profile(id)
    if not value: raise HTTPException(400,'Create your profile or load the demo first.')
    return value

@app.get('/health')
def health(): return {'status':'healthy','engine':'LangGraph','mode':'local','generation':'Local Ollama model' if os.getenv('ENABLE_LOCAL_LLM')=='true' else 'Grounded templates and rubric-based coaching'}

def profile_ready(profile):
    if not profile: return False
    p=profile['personal_details']
    return bool(p['email'].split('@')[-1] not in {'example.com','example.org','example.net'} and 'not specified' not in p['work_authorization'].lower() and not any(e['company']=='Example Studio' for e in profile['base_resume']['experience_history']))

def browser_path():
    return getattr(app.state, 'chromium_path', '')

@app.get('/api/v1/runtime')
def runtime():
    browser_ready=Path(browser_path()).is_file()
    conf=db.config()
    model=conf['llm_provider_config']['reasoning_model'] if conf else None
    model_ready=False
    if conf:
        try:
            import httpx
            tags=httpx.get(conf['llm_provider_config']['local_ollama_base_url'].rstrip('/')+'/api/tags',timeout=2,trust_env=False).json()
            model_ready=any(m['name']==model for m in tags.get('models',[]))
        except Exception: pass
    return {'model_ready':model_ready,'local_ai_enabled':os.getenv('ENABLE_LOCAL_LLM')=='true','model':model,'headless_enabled':os.getenv('ENABLE_LIVE_SUBMISSION')=='true','browser_installed':browser_ready,'profile_ready':profile_ready(db.profile())}

@app.get('/api/v1/profile')
def get_profile():
    profile = db.profile()
    return {**profile, '_revision': db.profile_revision(profile)} if profile else None

@app.post('/api/v1/profile')
def save_profile(profile: UserProfile, request: Request = None):
    if profile.user_id!='local': raise HTTPException(400,'This local edition uses user_id "local".')
    with profile_write:
        expected = request.headers.get('if-match') if request else None
        if expected and expected != db.profile_revision(db.profile()):
            raise HTTPException(409,'Your profile changed in another editor. Reopen My profile or reload candidate evidence, then reapply your edits to the latest version.')
        p=profile.personal_details.model_dump();p.update(user_id=profile.user_id,base_resume_json=profile.base_resume.model_dump_json(),eeo_demographics_json=profile.eeo_demographics.model_dump_json() if profile.eeo_demographics else None)
        cols=list(p)
        db.execute(f"INSERT INTO user_profiles ({','.join(cols)}) VALUES ({','.join(':'+k for k in cols)}) ON CONFLICT(user_id) DO UPDATE SET "+','.join(f'{k}=excluded.{k}' for k in cols if k!='user_id')+',updated_at=CURRENT_TIMESTAMP',p)
        if not db.config(): save_config(SystemVariables(**demo.CONFIG))
        return {'status':'success','user_id':profile.user_id,'_revision':db.profile_revision(db.profile())}

@app.get('/api/v1/config')
def get_config(): return db.config() or demo.CONFIG

@app.post('/api/v1/config')
def save_config(config: SystemVariables):
    require_profile()
    db.execute('INSERT OR REPLACE INTO system_config (config_id,user_id,search_criteria_json,execution_preferences_json,llm_config_json) VALUES (:id,:id,:criteria,:prefs,:llm)',{'id':'local','criteria':config.job_search_criteria.model_dump_json(),'prefs':config.execution_preferences.model_dump_json(),'llm':config.llm_provider_config.model_dump_json()})
    return {'status':'success'}

class ImportJob(BaseModel):
    company_name: str = Field(min_length=1, max_length=150)
    job_title: str = Field(min_length=1, max_length=200)
    job_url: str
    description: str = Field(min_length=20, max_length=50000)
    location: str
    employment_type: str = 'Full-time'
    requisition_id: str | None = Field(default=None,max_length=100)
    posted_at: str | None = None
    source: str = Field(default='',max_length=100)

@app.post('/api/v1/jobs/import')
def import_job(body: ImportJob):
    parsed=urlparse(body.job_url)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username: raise HTTPException(400,'Use a valid HTTPS application URL.')
    p=require_profile()
    result=discovery_graph.invoke({'jobs':[body.model_dump()],'profile':p,'criteria':db.config()['job_search_criteria']})
    return {'message':'Opportunity imported.' if result['count'] else 'Already saved; no duplicate added.' if result.get('matched') else 'This job was excluded by your search preferences.', 'count':result['count']}

class SearchRequest(BaseModel):
    provider: str='demo'
    board: str=''
    keywords: str=Field(default='',max_length=200)
    location: str=Field(default='',max_length=200)
    limit: int=Field(default=20,ge=1,le=100)
    sources: List[str]=Field(default_factory=list,max_length=40)
    boards: dict[str,str]=Field(default_factory=dict,max_length=4)
    page_url: str=Field(default='',max_length=2000)
    max_posting_age_days: int | None = Field(default=None,ge=1,le=365)
    override_posting_age: bool = False

@app.get('/api/v1/jobs/sources')
def job_sources(include_unavailable:bool=False): return source_catalog(include_unavailable)

@app.post('/api/v1/jobs/search')
def search(body:SearchRequest, user_id:str='local'):
    p=require_profile(user_id);c=db.config(user_id)
    if body.provider=='demo' and not body.sources:
        incoming=demo.jobs()
        result=discovery_graph.invoke({'jobs':incoming,'profile':p,'criteria':c['job_search_criteria']})
        return {'message':f"Discovery complete: {result['count']} opportunities match your filters.",'count':result['count']}
    providers=list(dict.fromkeys(body.sources or [body.provider]))
    if any(x not in {r['id'] for r in SOURCE_INFO} for x in providers): raise HTTPException(400,'Unknown discovery source.')
    criteria=dict(c['job_search_criteria'])
    if body.location.strip():criteria['target_locations']=[body.location.strip()]
    if body.override_posting_age:criteria['max_posting_age_days']=body.max_posting_age_days
    from collections import Counter
    from backend.services.job_matching import exclusions
    reports=[];total=0
    from concurrent.futures import ThreadPoolExecutor
    def fetch_source(provider):
        try:
            return discover_source(provider,board=body.boards.get(provider,body.board),keywords=body.keywords.strip(),location=body.location.strip(),limit=body.limit,page_url=body.page_url)
        except Exception as exc:return exc
    with ThreadPoolExecutor(max_workers=4) as pool:
        fetched=list(pool.map(fetch_source,providers))
    for provider,source_result in zip(providers,fetched):
        try:
            if isinstance(source_result,Exception):raise source_result
            incoming,cached=source_result
            result=discovery_graph.invoke({'jobs':incoming,'profile':p,'criteria':criteria,'skip_seen':True})
            total+=result['count']
            reports.append({'source':provider,'status':'success','fetched':len(incoming),'matched':result['count'],'already_seen':result.get('skipped',0),'cached':cached,'excluded_reasons':dict(Counter(reason for j in incoming for reason in exclusions(j,criteria))),'incomplete_descriptions':sum(bool(j.get('description_incomplete')) for j in incoming)})
        except Exception as exc:
            reports.append({'source':provider,'status':'unavailable','message':str(exc)[:500],'fetched':0,'matched':0})
    return {'message':f'Discovery finished: {total} new opportunities; {sum(r.get("already_seen",0) for r in reports)} previously seen or duplicate postings skipped across {sum(r["status"]=="success" for r in reports)} available sources.','count':total,'sources':reports}

@app.post('/api/v1/demo')
def load_demo():
    if not db.profile(): save_profile(UserProfile(**demo.PROFILE))
    return search(SearchRequest())

@app.get('/api/v1/applications')
def applications(status:Optional[ApplicationStatus]=None,phase:str='all'):
    if phase not in {'all','new','reviewing'}:raise HTTPException(400,'Unknown opportunity phase.')
    phases={'new':{'DISCOVERED','MATCHED'},'reviewing':{'REVIEWING','QUEUED','TAILORED'}}
    return [j for j in db.applications() if (not status or j['status']==status.value) and (phase=='all' or j['status'] in phases[phase])]

@app.get('/api/v1/applications/deleted')
def deleted_opportunities():
    return db.query('SELECT a.job_id,a.company_name,a.job_title,d.deleted_at FROM deleted_opportunities d JOIN application_records a ON a.job_id=d.job_id ORDER BY d.deleted_at DESC')

class OpportunityIDs(BaseModel):
    job_ids:List[str]=Field(min_length=1,max_length=100)

@app.post('/api/v1/applications/review')
def review_opportunities(body:OpportunityIDs,tasks:BackgroundTasks):
    from backend.services import studio_store
    from backend.studio_api import generate_review
    with queue_reservation:
        ids=list(dict.fromkeys(body.job_ids));jobs=[require_job(id) for id in ids]
        if any(j['status'] not in {'DISCOVERED','MATCHED','TAILORED','REVIEWING'} for j in jobs):raise HTTPException(409,'Only new or reviewing opportunities can be moved into review.')
        for id in ids:
            db.execute("UPDATE application_records SET status='REVIEWING',updated_at=CURRENT_TIMESTAMP WHERE job_id=:id",{'id':id})
            token=studio_store.reserve(id)
            if token:tasks.add_task(generate_review,id,token)
    return {'reviewing':ids,'message':f'{len(ids)} opportunities moved to Reviewing. Application Studio prepares missing kits in the background.'}

@app.post('/api/v1/applications/delete')
def delete_opportunities(body:OpportunityIDs):
    with queue_reservation:
        ids=list(dict.fromkeys(body.job_ids))
        # Validate the entire request before changing anything.
        for id in ids:
            rows=db.query('SELECT status FROM application_records WHERE job_id=:id',{'id':id})
            if not rows:raise HTTPException(404,'Opportunity not found.')
            if rows[0]['status']=='QUEUED':raise HTTPException(409,'Wait for preparation or submission to finish before deleting this opportunity.')
        with db.engine.begin() as conn:
            for id in ids:conn.execute(db.text('INSERT OR IGNORE INTO deleted_opportunities (job_id) VALUES (:id)'),{'id':id})
        from backend.services.studio_store import remove_artifacts
        for id in ids:remove_artifacts(id)
    return {'deleted':ids,'message':f'{len(ids)} opportunities deleted with their application kits and generated data. The job listing can be restored; documents must be regenerated.'}

@app.post('/api/v1/applications/restore')
def restore_opportunities(body:OpportunityIDs):
    with queue_reservation:
        for id in body.job_ids:
            if not db.query('SELECT job_id FROM application_records WHERE job_id=:id',{'id':id}):raise HTTPException(404,'Opportunity not found.')
        with db.engine.begin() as conn:
            for id in set(body.job_ids):conn.execute(db.text('DELETE FROM deleted_opportunities WHERE job_id=:id'),{'id':id})
    return {'restored':list(dict.fromkeys(body.job_ids))}


@app.post('/api/v1/applications/batch-apply')
def batch(job_ids:List[str],background_tasks:BackgroundTasks,submit:bool=False):
    with queue_reservation:
        return reserve_batch(job_ids,background_tasks,submit)

def reserve_batch(job_ids,background_tasks,submit=False):
    ids=list(dict.fromkeys(job_ids))
    if not ids: raise HTTPException(400,'Select at least one opportunity.')
    jobs=[require_job(id) for id in ids]
    config=db.config()
    if not config: raise HTTPException(400,'Save your profile first.')
    if submit:
        if os.getenv('ENABLE_LIVE_SUBMISSION')!='true' or not config['execution_preferences']['enable_headless_auto_apply']: raise HTTPException(409,'Headless submission is not enabled.')
        if not profile_ready(db.profile()): raise HTTPException(400,'Replace all demo profile details and work authorization before submitting real applications.')
        if any(j.get('demo') for j in jobs): raise HTTPException(400,'Demo opportunities cannot be submitted.')
        if any(j['status']!='TAILORED' or not j['tailored_resume_path'] for j in jobs): raise HTTPException(409,'Prepare and review the documents before submission.')
        if any(j['classification']!='HEADLESS_AUTO' or j['match_score']<config['execution_preferences']['auto_apply_threshold_score'] for j in jobs): raise HTTPException(409,'This opportunity requires browser-assisted application.')
    daily=config['execution_preferences']['max_daily_applications']
    used=db.query("SELECT COUNT(*) n FROM application_records WHERE status='QUEUED' OR (status='APPLIED' AND date(updated_at)=date('now'))")[0]['n']
    if len(ids)+used>daily: raise HTTPException(400,'This batch exceeds your remaining daily application limit.')
    for j in jobs:
        if j['status'] not in ['DISCOVERED','MATCHED','TAILORED','REVIEWING']: raise HTTPException(409,'Only new or reviewing applications can be queued.')
        if any('unconfirmed' in l['action'].lower() for l in j['submission_logs']): raise HTTPException(409,'Review the unconfirmed submission on the employer portal before retrying.')
        if not submit and resumes.selected(j['job_id']) not in {None,'profile'}:
            raise HTTPException(409,'Preparation uses the fixed template and your saved profile. Review the upload in My documents, add its verified facts to Candidate evidence in Application Studio, and select Profile resume before preparing. The original upload remains available for manual applications.')
    for j in jobs:
        # Low-score jobs can be tailored but are always routed to human review.
        if j['match_score']<config['execution_preferences']['auto_apply_threshold_score']:
            db.execute("UPDATE application_records SET classification='HUMAN_IN_THE_LOOP_LINK' WHERE job_id=:id",{'id':j['job_id']})
        if not submit: resumes.select(j['job_id'],'profile')
        db.execute("UPDATE application_records SET status='QUEUED' WHERE job_id=:id",{'id':j['job_id']})
    background_tasks.add_task(run_batch,ids,submit=submit)
    return {'message':f'Queued {len(ids)} applications for '+('submission.' if submit else 'document preparation and review.')}

class StatusUpdate(BaseModel):
    status:ApplicationStatus

@app.patch('/api/v1/applications/{job_id}')
def update_status(job_id:str,body:StatusUpdate,tasks:BackgroundTasks):
    with queue_reservation:
        if body.status==ApplicationStatus.REVIEWING:return review_opportunities(OpportunityIDs(job_ids=[job_id]),tasks)
        return _update_status(job_id,body)

def _update_status(job_id,body):
    job=require_job(job_id)
    allowed={'DISCOVERED':['MATCHED','REJECTED'],'MATCHED':['APPLIED','REJECTED'],'REVIEWING':['APPLIED','REJECTED'],'TAILORED':['APPLIED','REJECTED'],'APPLIED':['INTERVIEWING','REJECTED'],'INTERVIEWING':['OFFER','REJECTED'],'REJECTED':['MATCHED'],'OFFER':[],'QUEUED':[]}
    if body.status.value not in allowed[job['status']]: raise HTTPException(409,'This status transition is not available.')
    db.execute('UPDATE application_records SET status=:status,updated_at=CURRENT_TIMESTAMP WHERE job_id=:id',{'id':job_id,'status':body.status.value})
    log(job_id,'SUCCESS',f'Status manually updated to {body.status.value}')
    return {'status':body.status.value}

@app.get('/api/v1/extension/fill-context/{job_id}')
def fill_context(job_id:str):
    job=require_job(job_id)
    return {'job_id':job_id,'job_url':job['job_url'],'fields':fields(require_profile(job['user_id'])),'resume_url':f'http://localhost:8000/api/v1/applications/{job_id}/document/resume' if job['tailored_resume_path'] else None}

@app.get('/api/v1/applications/{job_id}/document/{kind}')
def document(job_id:str,kind:str):
    if kind not in ['resume','cover-letter']: raise HTTPException(404,'Unknown document')
    job=require_job(job_id);path=job['tailored_resume_path' if kind=='resume' else 'tailored_cover_letter_path']
    if not path or not Path(path).is_file(): raise HTTPException(404,'Prepare this application to generate documents.')
    return FileResponse(path,filename=f"{job['company_name']}-{kind}."+('pdf' if kind=='resume' else 'txt'))

@app.post('/api/v1/interview/generate-questions',response_model=List[InterviewQuestion])
def generate(job_id:str): return questions(require_job(job_id))

class Answer(BaseModel):
    job_id:str
    question_id:str
    answer:str=Field(min_length=10,max_length=20000)

@app.post('/api/v1/interview/evaluate',response_model=UserAnswerFeedback)
def evaluate(body:Answer):
    question=next((q for q in questions(require_job(body.job_id)) if q['id']==body.question_id),None)
    if not question: raise HTTPException(404,'Question not found')
    return feedback(question,body.answer)
