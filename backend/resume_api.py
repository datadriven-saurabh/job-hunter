import json
from pathlib import Path
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from backend import database as db
from backend.services import resumes

router=APIRouter(prefix='/api/v1')

@router.get('/resumes')
def list_resumes():return resumes.listing()

@router.post('/resumes/upload')
async def upload_resume(file:UploadFile=File(...),label:str=Form('')):
    if len(label)>120:raise HTTPException(422,'Resume label must be at most 120 characters.')
    content=await file.read(resumes.MAX_BYTES+1)
    try:
        record,created=resumes.upload(content,file.filename or '',label)
        return {'resume_id':record['resume_id'],'label':record['label'],'keywords':record['keywords'],'created':created,'message':'Resume uploaded and indexed locally.' if created else 'This file is already in your resume library.'}
    except Exception as exc:raise HTTPException(400,str(exc) if isinstance(exc,ValueError) else 'Could not read this file. Upload a valid PDF, DOCX, or UTF-8 TXT resume.')
    finally:await file.close()

class ResumeUpdate(BaseModel):
    label:str=Field(min_length=1,max_length=120)

@router.patch('/resumes/{resume_id}')
def rename(resume_id:str,body:ResumeUpdate):
    if resume_id=='profile':raise HTTPException(400,'The profile resume is named automatically.')
    try:resumes.get(resume_id)
    except ValueError as exc:raise HTTPException(404,str(exc))
    db.execute('UPDATE resumes SET label=:label WHERE resume_id=:id',{'id':resume_id,'label':body.label.strip()})
    return {'status':'saved'}

@router.get('/resumes/{resume_id}')
def details(resume_id:str):
    try:r=resumes.get(resume_id)
    except ValueError as exc:raise HTTPException(404,str(exc))
    return {k:v for k,v in r.items() if k not in {'path','sha256'}}

@router.get('/resumes/{resume_id}/download')
def download(resume_id:str):
    try:r=resumes.get(resume_id)
    except ValueError as exc:raise HTTPException(404,str(exc))
    if not r.get('path'):raise HTTPException(400,'The profile resume is generated when you prepare an application.')
    return FileResponse(r['path'],filename=r['original_name'])

@router.get('/applications/{job_id}/resume-matches')
def matches(job_id:str):
    job=db.get_job(job_id)
    if not job:raise HTTPException(404,'Application not found.')
    ranked=resumes.recommendations(job)
    return {'matches':ranked,'selected_resume_id':resumes.selected(job_id),'recommended_resume_id':ranked[0]['resume_id'] if ranked and ranked[0]['score']>0 else None,'method':'TF-IDF cosine similarity over local resume text and the job description.'}

class Selection(BaseModel):
    resume_id:str

@router.post('/applications/{job_id}/resume')
def choose(job_id:str,body:Selection):
    job=db.get_job(job_id)
    if not job:raise HTTPException(404,'Application not found.')
    if job['status'] not in {'DISCOVERED','MATCHED','TAILORED'}:raise HTTPException(409,'Resume selection is locked while processing or after submission.')
    try:resumes.get(body.resume_id)
    except ValueError as exc:raise HTTPException(404,str(exc))
    if resumes.selected(job_id)!=body.resume_id:
        resumes.select(job_id,body.resume_id)
        db.execute("UPDATE application_records SET status='MATCHED',tailored_resume_path=NULL,tailored_cover_letter_path=NULL WHERE job_id=:id",{'id':job_id})
    return {'status':'selected','resume_id':body.resume_id}
