import json
import re
import uuid
import shutil
from urllib.parse import urlparse
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field
from bs4 import BeautifulSoup
from backend import database as db
from backend.state import queue_reservation
from backend.services import studio_store as store
from backend.agents.job_sources import public_get, jsonld_jobs, ALLOWED, SourceUnavailable
from backend.services.career_generator import generateATSResume, generateCoverLetter, generateLinkedInReferralMessage
from backend.services.career_render import render_resume,render_cover
from backend.ai.router import ModelRouter
from backend.prompts import RESUME_FORMAT
from backend.services.career_validation import words,validate_referral
from backend.services.job_intelligence import enrich
from backend.services.outreach import drafts

router=APIRouter(prefix='/api/v1/studio')
# Fixed hosts only; redirects are checked by public_get. No cookies or private addresses.
JOB_HOSTS={'jobs.lever.co','boards.greenhouse.io','job-boards.greenhouse.io','job-boards.eu.greenhouse.io','jobs.ashbyhq.com','jobs.smartrecruiters.com','careers.smartrecruiters.com','apply.workable.com','jobs.workable.com','www.arbeitnow.com','www.arbeitnow.co.uk'}
ALLOWED.update(JOB_HOSTS)

class Resolve(BaseModel):
    url:str=Field(max_length=2000)

@router.post('/resolve')
def resolve(body:Resolve):
    try:
        parsed=urlparse(body.url);port=parsed.port
    except ValueError:raise HTTPException(400,'Invalid job URL.')
    if parsed.scheme!='https' or parsed.hostname not in ALLOWED or parsed.username or parsed.password or port not in {None,443}:raise HTTPException(400,'Use a supported public job-board HTTPS URL, or paste the description below. Private/custom hosts are not fetched.')
    try:
        response=public_get(body.url)
        structured=jsonld_jobs(response.text,source=parsed.hostname,page_url=body.url)
        if len(structured)==1:return dict(structured[0],description_incomplete=False,review_required=True)
        soup=BeautifulSoup(response.text,'html.parser')
        for t in soup(['script','style','nav','footer','header']):t.decompose()
        description=soup.select_one('.show-more-less-html__markup, .description__text, .job-description, [itemprop="description"], main')
        title=soup.select_one('h1');company=soup.select_one('.topcard__org-name-link, [itemprop="hiringOrganization"]')
        return {'job_url':body.url,'job_title':title.get_text(' ',strip=True) if title else '', 'company_name':company.get_text(' ',strip=True) if company else '', 'location':'','description':description.get_text('\n',strip=True)[:25000] if description else '', 'description_incomplete':True,'review_required':True,'message':'Review extracted text and enter any missing company/title. If the page needs JavaScript or login, paste its job description.'}
    except Exception as e:raise HTTPException(400,'Could not read this public posting. Paste its title, company and full description. '+str(e)[:180])

class KitRequest(BaseModel):
    job_id:str=''
    job_title:str=Field(default='',max_length=200)
    company_name:str=Field(default='',max_length=200)
    job_url:str=Field(default='',max_length=2000)
    description:str=Field(default='',max_length=30000)
    location:str=Field(default='',max_length=300)
    recipient:str=Field(default='',max_length=100)
    requisition_id:str=Field(default='',max_length=100)
    resume_url:str=Field(default='',max_length=2000)
    shared_context:str=Field(default='',max_length=300)
    message_type:str=Field(default='post_connection',pattern='^(post_connection|mutual_group)$')

class KitUpdate(BaseModel):
    cover_letter:str=Field(max_length=12000)
    connection_note:str=Field(max_length=299)
    referral_message:str=Field(max_length=6000)

def directory(id):
    if not re.fullmatch(r'[a-f0-9]{32}',id):raise HTTPException(404,'Draft not found.')
    if not db.query('SELECT kit_id FROM studio_kits WHERE kit_id=:id',{'id':id}):raise HTTPException(404,'Draft not found.')
    path=db.DATA/'kits'/id
    if not (path/'kit.json').exists():raise HTTPException(404,'Draft not found.')
    return path

@router.get('/jobs/{job_id}')
def job_workspace(job_id:str):
    return store.workspace(job_id)

@router.post('/jobs/{job_id}/retry')
def retry_workspace(job_id:str,tasks:BackgroundTasks):
    token=store.reserve(job_id,reuse=False)
    if token:tasks.add_task(generate_review,job_id,token)
    return {'state':'queued' if token else 'running'}

def generate_review(job_id,token):
    with store.generation_worker:
        with queue_reservation:
            if not store.current(job_id,token):return
            store.finish(job_id,token,'running')
            job=db.get_job(job_id);profile=db.profile()
        try:
            _generate_kit(KitRequest(job_id=job_id),profile,job,token)
        except Exception as exc:
            with queue_reservation:
                message=exc.detail if isinstance(exc,HTTPException) else 'Preparation failed. Review your profile and retry from Application Studio.'
                store.finish(job_id,token,'failed',str(message)[:500])

@router.post('/kits')
def create(body:KitRequest):
    with queue_reservation:
        profile=db.profile()
        if not profile:raise HTTPException(400,'Save My profile first.')
        if body.job_id:job=db.get_job(body.job_id)
        else:
            from backend.agents.scout_agent import job_id
            job=db.get_job(job_id(body.job_url)) or body.model_dump()
        if not job:raise HTTPException(404,'Job not found.')
        linked=job.get('job_id') or None
        token=store.reserve(linked,reuse=False) if linked else None
        if linked and not token:raise HTTPException(409,'A kit is already being prepared for this opportunity.')
    try:return _generate_kit(body,profile,job,token)
    except Exception:
        with queue_reservation:
            if linked:store.finish(linked,token,'failed','Preparation failed. Review required profile and job details, then retry.')
        raise

def _generate_kit(body,profile,job,token=None):
    if not all(str(job.get(k,'')).strip() for k in ['job_title','company_name','job_url']) or len(job.get('description','').strip())<80:raise HTTPException(400,'Provide company, title, job URL and a full description of at least 80 characters.')
    parsed=urlparse(job['job_url'])
    if parsed.scheme!='https' or not parsed.hostname or parsed.username:raise HTTPException(400,'Use a valid HTTPS job URL.')
    if body.requisition_id:job=dict(job,requisition_id=body.requisition_id)
    job=enrich(job)
    id=uuid.uuid4().hex;path=db.DATA/'kits'/'.pending'/id;path.mkdir(parents=True,exist_ok=True)
    try:
        router=ModelRouter();router.cache_enabled=False
        try:
            assets={'resume':generateATSResume(profile,job,router=router),
                    'cover_letter':generateCoverLetter(profile,job,router=router,recipient=body.recipient),
                    'connection_note':generateLinkedInReferralMessage(profile,job,'invite_note',recipient=body.recipient,resume_url=body.resume_url),
                    'referral_message':generateLinkedInReferralMessage(profile,job,body.message_type,recipient=body.recipient,resume_url=body.resume_url,shared_context=body.shared_context)}
        except ValueError as e:
            shutil.rmtree(path,ignore_errors=True)
            raise HTTPException(400,str(e))
        for name,renderer in [('resume',render_resume),('cover_letter',render_cover)]:
            asset=assets[name]
            if asset['status']=='valid':
                try:renderer(asset,path)
                except ValueError as e:
                    asset['status']='needs_user_input';asset['validation']['valid']=False
                    asset['validation']['errors'].append({'code':'page_layout','message':str(e)})
        leads=drafts(job,profile,body.recipient)
        kit={k:leads[k] for k in ['named_contacts','contact_searches','contact_note']}
        from datetime import datetime,timezone
        kit.update(id=id,created_at=datetime.now(timezone.utc).isoformat(),job=job,assets=assets,template=RESUME_FORMAT,resume_source='Saved My profile; verified evidence',resume_pages=1 if assets['resume']['status']=='valid' else None,
                   resume_markdown=assets['resume']['preview'],**{k:assets[k]['preview'] for k in ['cover_letter','connection_note','referral_message']},
                   generation_options={'recipient':body.recipient,'resume_url':body.resume_url,'shared_context':body.shared_context,'message_type':body.message_type,'requisition_id':body.requisition_id},model_usage=router.events)
        with queue_reservation:
            linked=job.get('job_id') or None
            if linked and not store.current(linked,token):
                shutil.rmtree(path,ignore_errors=True)
                raise HTTPException(409,'This opportunity was deleted or preparation was cancelled.')
            store.write_kit(path,kit)
            path.rename(db.DATA/'kits'/id)
            db.execute('INSERT INTO studio_kits(kit_id,job_id) VALUES (:kit,:job)',{'kit':id,'job':linked})
            if linked:store.finish(linked,token,store.kit_state(kit))
        return kit
    finally:
        shutil.rmtree(path,ignore_errors=True)

@router.get('/kits')
def list_kits(job_id:str|None=None):
    if job_id and not store.active(job_id):raise HTTPException(404,'Opportunity not found.')
    rows=db.query('SELECT kit_id FROM studio_kits '+('WHERE job_id=:id ' if job_id else '')+'ORDER BY created_at DESC,rowid DESC',{'id':job_id})
    result=[]
    for row in rows:
        path=db.DATA/'kits'/row['kit_id']/'kit.json'
        if path.is_file():result.append(json.loads(path.read_text()))
    return result

@router.get('/kits/{id}')
def read_kit(id:str):return json.loads((directory(id)/'kit.json').read_text())

@router.patch('/kits/{id}')
def edit(id:str,body:KitUpdate):
    with queue_reservation:return _edit(id,body)

def _edit(id,body):
    path=directory(id);kit=json.loads((path/'kit.json').read_text())
    if 'assets' not in kit:raise HTTPException(409,'Regenerate this legacy kit to use the validated pipeline.')
    changes=body.model_dump();errors=[]
    for key,value in changes.items():
        asset=kit['assets'][key]
        if value==kit[key]:continue
        if key=='cover_letter':
            parts=value.strip().split('\n\n')
            if not 250<=words(value)<=400 or len(parts)!=7:
                errors.append('Cover letter edits must retain the header, salutation, four paragraphs and sign-off, with 250–400 total words.');continue
            asset['data'].update(header=parts[0],salutation=parts[1],paragraphs=parts[2:6],signoff=parts[6])
        else:
            data=asset['data'];report=validate_referral(value,asset['asset_type'],kit['job']['job_title'],data['requisition_id'],data['resume_url'],data['skills'])
            if report.errors:errors.extend(e['message'] for e in report.errors);continue
            if asset.get('missing_inputs'):errors.extend(asset['missing_inputs']);continue
        asset.update(text=value,preview=value,status='valid')
        asset['validation'].update(valid=True,word_count=words(value),character_count=len(value),errors=[],warnings=['User-edited draft: factual changes require your review.'])
        asset['generation_method']='User-edited; format and required-field checks repeated'
        kit[key]=value
    if errors:raise HTTPException(422,' '.join(errors))
    if changes['cover_letter']!=json.loads((path/'kit.json').read_text())['cover_letter']:
        staged=path/'edited-cover'
        try:
            rendered=render_cover(kit['assets']['cover_letter'],staged)
            from pathlib import Path
            Path(rendered).replace(path/'cover-letter.pdf')
        except ValueError as e:raise HTTPException(422,str(e))
    store.write_kit(path,kit)
    job_id=kit.get('job',{}).get('job_id')
    if job_id and store.latest(job_id) and store.latest(job_id).get('id')==id:
        rows=db.query('SELECT token FROM studio_runs WHERE job_id=:id',{'id':job_id})
        if rows:store.finish(job_id,rows[0]['token'],store.kit_state(kit))
    return kit

@router.get('/kits/{id}/resume')
def download_resume(id:str):
    path=directory(id);kit=json.loads((path/'kit.json').read_text())
    if kit.get('assets',{}).get('resume',{}).get('status') not in {None,'valid'} or not (path/'resume.pdf').exists():raise HTTPException(409,'Complete the resume validation requirements before export.')
    return FileResponse(path/'resume.pdf',filename='resume-one-page.pdf')

@router.get('/kits/{id}/resume-markdown')
def download_markdown(id:str):
    kit=json.loads((directory(id)/'kit.json').read_text())
    if kit.get('assets',{}).get('resume',{}).get('status')!='valid':raise HTTPException(409,'Complete resume validation first.')
    return PlainTextResponse(kit['resume_markdown'],headers={'Content-Disposition':'attachment; filename="resume.md"'})

@router.get('/kits/{id}/cover-pdf')
def download_cover_pdf(id:str):
    path=directory(id);kit=json.loads((path/'kit.json').read_text())
    if kit.get('assets',{}).get('cover_letter',{}).get('status')!='valid' or not (path/'cover-letter.pdf').exists():raise HTTPException(409,'Complete cover letter validation first.')
    return FileResponse(path/'cover-letter.pdf',filename='cover-letter.pdf')

@router.get('/kits/{id}/{kind}')
def download_text(id:str,kind:str):
    if kind not in {'cover_letter','connection_note','referral_message'}:raise HTTPException(404,'Document not found.')
    kit=json.loads((directory(id)/'kit.json').read_text())
    if kit.get('assets',{}).get(kind,{}).get('status') not in {None,'valid'}:raise HTTPException(409,'Resolve required fields and length checks before exporting this draft.')
    return PlainTextResponse(kit[kind],headers={'Content-Disposition':f'attachment; filename="{kind}.txt"'})

class KitAnswers(BaseModel):
    questions:list[str]=Field(min_length=1,max_length=10)
    max_words:int=Field(default=150,ge=1,le=500)
    max_characters:int|None=Field(default=None,ge=1,le=10000)

@router.post('/kits/{id}/answers')
def saved_answers(id:str,body:KitAnswers):
    from backend.services.application_answers import answer_questions
    if any(not q.strip() or len(q)>2000 for q in body.questions):raise HTTPException(422,'Each question must have 1–2,000 characters.')
    with queue_reservation:
        path=directory(id);kit=json.loads((path/'kit.json').read_text());profile=db.profile()
    if not profile:raise HTTPException(400,'Save My profile first.')
    model=ModelRouter();model.cache_enabled=False
    answers=answer_questions(profile,kit['job'],[{'question':q,'max_words':body.max_words,'max_characters':body.max_characters,'mode':'draft'} for q in body.questions],router=model,use_cache=False)
    result={**body.model_dump(),'answers':answers}
    with queue_reservation:
        path=directory(id)  # Deletion during generation must not recreate a kit.
        kit=json.loads((path/'kit.json').read_text());kit['application_answers']=result;store.write_kit(path,kit)
    return result
