import json
from pathlib import Path
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from backend import database as db
from backend.services import resumes
from backend.state import queue_reservation

router=APIRouter(prefix='/api/v1')

@router.get('/resumes')
def list_resumes():return resumes.listing()

@router.post('/resumes/upload')
async def upload_resume(file:UploadFile=File(...),label:str=Form('')):
    if len(label)>120:raise HTTPException(422,'Resume label must be at most 120 characters.')
    content=await file.read(resumes.MAX_BYTES+1)
    try:
        record,created=resumes.upload(content,file.filename or '',label)
        try:
            from backend.services.resume_intake import profile_draft
            draft=profile_draft(record['text'],db.profile(),record['resume_id'])
        except Exception:
            draft={'profile':db.profile(),'resume_id':record['resume_id'],'suggested_titles':[],'missing_fields':[],'warnings':['The file was uploaded, but its profile draft could not be parsed. Open it in My documents and enter profile facts manually.'],'review_required':True,'saved':False,'method':'Parser unavailable; manual review required.'}
        return {'profile_draft':draft,'resume_id':record['resume_id'],'label':record['label'],'keywords':record['keywords'],'created':created,'message':'Resume uploaded and indexed locally.' if created else 'This file is already in your resume library.'}
    except Exception as exc:raise HTTPException(400,str(exc) if isinstance(exc,ValueError) else 'Could not read this file. Upload a valid PDF, DOCX, or UTF-8 TXT resume.')
    finally:await file.close()

class ResumeUpdate(BaseModel):
    label:str=Field(min_length=1,max_length=120)
    @field_validator('label')
    @classmethod
    def nonblank(cls,value):
        if not value.strip():raise ValueError('Enter a resume name.')
        return value.strip()

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
    with queue_reservation:
        return _choose(job_id,body)

def _choose(job_id,body):
    job=db.get_job(job_id)
    if not job:raise HTTPException(404,'Application not found.')
    if job['status'] not in {'DISCOVERED','MATCHED','TAILORED','REVIEWING'}:raise HTTPException(409,'Resume selection is locked while processing or after submission.')
    try:resumes.get(body.resume_id)
    except ValueError as exc:raise HTTPException(404,str(exc))
    if resumes.selected(job_id)!=body.resume_id:
        resumes.select(job_id,body.resume_id)
        db.execute("UPDATE application_records SET status=CASE WHEN status='REVIEWING' THEN 'REVIEWING' ELSE 'MATCHED' END,tailored_resume_path=NULL,tailored_cover_letter_path=NULL WHERE job_id=:id",{'id':job_id})
    return {'status':'selected','resume_id':body.resume_id}

@router.delete('/resumes/{resume_id}')
def delete_resume(resume_id:str):
    if resume_id=='profile':raise HTTPException(400,'Edit My profile to change the profile resume.')
    with queue_reservation:
        try:record=resumes.get(resume_id)
        except ValueError as exc:raise HTTPException(404,str(exc))
        if db.query("SELECT a.job_id FROM application_records a JOIN application_resume_selection s ON s.job_id=a.job_id WHERE s.resume_id=:id AND a.status='QUEUED'",{'id':resume_id}):raise HTTPException(409,'This resume is in use by a queued application. Wait for it to finish.')
        path=Path(record['path']).resolve();root=(db.DATA/'resumes').resolve()
        if root not in path.parents:raise HTTPException(409,'Resume storage path is invalid.')
        path.unlink(missing_ok=True)
        with db.engine.begin() as conn:
            conn.execute(db.text('DELETE FROM application_resume_selection WHERE resume_id=:id'),{'id':resume_id})
            conn.execute(db.text('DELETE FROM resumes WHERE resume_id=:id'),{'id':resume_id})
    return {'deleted':resume_id,'message':'Resume and its extracted text deleted. Your saved profile and application kits are retained.'}

@router.post('/resumes/{resume_id}/profile-draft')
def resume_profile(resume_id:str):
    try:record=resumes.get(resume_id)
    except ValueError as exc:raise HTTPException(404,str(exc))
    from backend.services.resume_intake import profile_draft
    return profile_draft(record['text'],db.profile(),resume_id)
