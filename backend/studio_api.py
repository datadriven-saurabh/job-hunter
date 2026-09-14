import json
import re
import uuid
from urllib.parse import urlparse
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field
from bs4 import BeautifulSoup
from backend import database as db
from backend.agents.job_sources import public_get, jsonld_jobs, ALLOWED, SourceUnavailable
from backend.services.onepage import build
from backend.services.outreach import drafts

router=APIRouter(prefix='/api/v1/studio')
# Fixed hosts only; redirects are checked by public_get. No cookies or private addresses.
JOB_HOSTS={'jobs.lever.co','boards.greenhouse.io','job-boards.greenhouse.io','job-boards.eu.greenhouse.io','jobs.ashbyhq.com','jobs.smartrecruiters.com','careers.smartrecruiters.com','apply.workable.com','jobs.workable.com','www.arbeitnow.com','www.arbeitnow.co.uk'}
ALLOWED.update(JOB_HOSTS)

class Resolve(BaseModel):
    url:str=Field(max_length=2000)

@router.post('/resolve')
def resolve(body:Resolve):
    parsed=urlparse(body.url)
    if parsed.scheme!='https' or parsed.hostname not in ALLOWED or parsed.username or parsed.password or parsed.port not in {None,443}:raise HTTPException(400,'Use a supported public job-board HTTPS URL, or paste the description below. Private/custom hosts are not fetched.')
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

class KitUpdate(BaseModel):
    cover_letter:str=Field(max_length=12000)
    connection_note:str=Field(max_length=200)
    referral_message:str=Field(max_length=6000)

def directory(id):
    if not re.fullmatch(r'[a-f0-9]{32}',id):raise HTTPException(404,'Draft not found.')
    path=db.DATA/'kits'/id
    if not (path/'kit.json').exists():raise HTTPException(404,'Draft not found.')
    return path

@router.post('/kits')
def create(body:KitRequest):
    profile=db.profile()
    if not profile:raise HTTPException(400,'Save My profile first.')
    job=db.get_job(body.job_id) if body.job_id else body.model_dump()
    if not job:raise HTTPException(404,'Job not found.')
    if not all(str(job.get(k,'')).strip() for k in ['job_title','company_name','job_url']) or len(job.get('description','').strip())<80:raise HTTPException(400,'Provide company, title, job URL and a full description of at least 80 characters.')
    parsed=urlparse(job['job_url'])
    if parsed.scheme!='https' or not parsed.hostname or parsed.username:raise HTTPException(400,'Use a valid HTTPS job URL.')
    id=uuid.uuid4().hex;path=db.DATA/'kits'/id
    try:build(job,profile,path)
    except ValueError as e:raise HTTPException(400,str(e))
    kit=dict(drafts(job,profile,body.recipient),id=id,job={k:job.get(k,'') for k in ['job_id','job_title','company_name','job_url','description','location']},resume_source='Saved My profile',resume_pages=1)
    (path/'kit.json').write_text(json.dumps(kit))
    return kit

@router.get('/kits')
def list_kits():
    paths=sorted((db.DATA/'kits').glob('*/kit.json'),key=lambda p:p.stat().st_mtime,reverse=True)
    return [json.loads(p.read_text()) for p in paths[:100]]

@router.patch('/kits/{id}')
def edit(id:str,body:KitUpdate):
    path=directory(id);kit=json.loads((path/'kit.json').read_text());kit.update(body.model_dump());(path/'kit.json').write_text(json.dumps(kit));return kit

@router.get('/kits/{id}/resume')
def download_resume(id:str):return FileResponse(directory(id)/'resume.pdf',filename='resume-one-page.pdf')

@router.get('/kits/{id}/{kind}')
def download_text(id:str,kind:str):
    if kind not in {'cover_letter','connection_note','referral_message'}:raise HTTPException(404,'Document not found.')
    kit=json.loads((directory(id)/'kit.json').read_text())
    return PlainTextResponse(kit[kind],headers={'Content-Disposition':f'attachment; filename="{kind}.txt"'})
