import json
import re
import uuid
from typing import Literal
from fastapi import APIRouter,HTTPException,BackgroundTasks
from pydantic import BaseModel,Field
from schemas import UserProfile
from backend import database as db
from backend.ai.router import ModelRouter,settings
from backend.ai.analysis import analyze_jobs
from backend.services.career_generator import generateATSResume,generateCoverLetter,generateLinkedInReferralMessage
from backend.services.application_answers import answer_questions
from backend.prompts import RESUME_FORMAT,PROMPT_VERSIONS

router=APIRouter(prefix='/api/v1/career')
class TargetJob(BaseModel):
    job_title:str=Field(min_length=1,max_length=200)
    company_name:str=Field(min_length=1,max_length=200)
    description:str=Field(min_length=80,max_length=30000)
    job_url:str=Field(default='',max_length=2000)
    location:str=Field(default='',max_length=300)
    requisition_id:str|None=Field(default=None,max_length=100)
    source:str=Field(default='',max_length=100)
    posted_at:str|None=None
class GenerationRequest(BaseModel):
    user_profile:UserProfile|str|None=None
    target_jd:TargetJob
    asset_type:Literal['resume','cover_letter','post_connection','invite_note','mutual_group']
    custom_format:str|None=Field(default=None,max_length=4000)
    recipient:str=Field(default='',max_length=100)
    resume_url:str=Field(default='',max_length=2000)
    shared_context:str=Field(default='',max_length=300)

def get_profile(value=None):
    result=(value if isinstance(value,str) else value.model_dump()) if value else db.profile()
    if not result:raise HTTPException(400,'Create My profile first.')
    return result

@router.get('/rules')
def rules():return {'template':RESUME_FORMAT,'prompt_versions':dict(PROMPT_VERSIONS),'limits':{'resume_words':[400,750],'cover_words':[250,400],'message_words':[75,125],'invite_characters_max':299},'conflict_policy':'Zero fabrication first. Fixed reference PDF controls visual layout. Clean Markdown has no icons/tables. Missing facts block export instead of producing invented text.'}

@router.post('/generate')
def generate(body:GenerationRequest):
    profile=get_profile(body.user_profile);job=body.target_jd.model_dump()
    try:
        if body.asset_type=='resume':return generateATSResume(profile,job,body.custom_format)
        if body.asset_type=='cover_letter':return generateCoverLetter(profile,job,recipient=body.recipient)
        return generateLinkedInReferralMessage(profile,job,body.asset_type,recipient=body.recipient,resume_url=body.resume_url,shared_context=body.shared_context)
    except ValueError as e:raise HTTPException(400,str(e))

class Question(BaseModel):
    question:str=Field(min_length=5,max_length=2000)
    max_words:int|None=Field(default=None,ge=1,le=500)
    max_characters:int|None=Field(default=None,ge=1,le=10000)
    mode:Literal['draft','autonomous']='draft'
class AnswersRequest(BaseModel):
    user_profile:UserProfile|str|None=None
    target_jd:TargetJob
    questions:list[Question]=Field(min_length=1,max_length=10)

@router.post('/answers')
def answers(body:AnswersRequest):
    try:return {'answers':answer_questions(get_profile(body.user_profile),body.target_jd.model_dump(),[q.model_dump() for q in body.questions])}
    except ValueError as e:raise HTTPException(400,str(e))

@router.get('/model-routing')
def routing():return settings()

class AnalyzeRequest(BaseModel):job_ids:list[str]=Field(min_length=1,max_length=10)

def analysis_path(id):
    if not re.fullmatch('[a-f0-9]{32}',id):raise HTTPException(404,'Analysis not found.')
    return db.DATA/'analysis-runs'/f'{id}.json'

def run_analysis(id,jobs,profile,criteria):
    try:result={'status':'complete',**analyze_jobs(jobs,profile,criteria)}
    except Exception:result={'status':'failed','message':'Analysis failed. Review model configuration; raw job facts were preserved.'}
    if db.HOSTED:
        db.execute('UPDATE analysis_runs SET payload=:payload,updated_at=CURRENT_TIMESTAMP WHERE id=:id',{'id':id,'payload':json.dumps(result)})
        return
    path=analysis_path(id)
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(result));tmp.replace(path)

@router.post('/analyze')
def analyze(body:AnalyzeRequest,tasks:BackgroundTasks):
    jobs=[db.get_job(id) for id in dict.fromkeys(body.job_ids)]
    if any(j is None for j in jobs):raise HTTPException(404,'Job not found.')
    profile=get_profile();id=uuid.uuid4().hex
    if db.HOSTED:db.execute('INSERT INTO analysis_runs(id,user_id,payload) VALUES (:id,:user_id,:payload)',{'id':id,'user_id':db.current_user(),'payload':json.dumps({'status':'running'})})
    else:
        path=analysis_path(id);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps({'status':'running'}))
    tasks.add_task(run_analysis,id,jobs,profile,db.config()['job_search_criteria']);return {'id':id,'status':'running'}

@router.get('/analyze/{id}')
def read_analysis(id:str):
    if db.HOSTED:
        rows=db.query('SELECT payload FROM analysis_runs WHERE id=:id',{'id':id})
        if not rows:raise HTTPException(404,'Analysis not found.')
        return json.loads(rows[0]['payload'])
    path=analysis_path(id)
    if not path.exists():raise HTTPException(404,'Analysis not found.')
    return json.loads(path.read_text())

class RoutingUpdate(BaseModel):
    model_tiers:dict[str,str]

@router.put('/model-routing')
def update_routing(body:RoutingUpdate):
    from backend.model_api import tags
    from schemas import LLMProviderConfig
    saved=db.config()
    if not saved:raise HTTPException(400,'Save your profile first.')
    installed={m['name'] for m in tags()}
    normalized={key:name if name in installed else name+':latest' for key,name in body.model_tiers.items()}
    if any(value not in installed for value in normalized.values()):raise HTTPException(400,'Choose installed models for every tier.')
    try:value=LLMProviderConfig(**{**saved['llm_provider_config'],'model_tiers':normalized}).model_dump()
    except ValueError:raise HTTPException(422,'Invalid model tier configuration.')
    db.execute('UPDATE system_config SET llm_config_json=:value WHERE user_id=:id',{'value':json.dumps(value),'id':'local'})
    return settings()

class IntakeRequest(BaseModel):
    raw_text:str=Field(min_length=80,max_length=30000)

@router.post('/profile-intake')
def profile_intake(body:IntakeRequest):
    from backend.services.profile_intake import parse_raw_profile
    try:return {'profile':parse_raw_profile(body.raw_text),'review_required':True,'saved':False}
    except ValueError as exc:raise HTTPException(400,str(exc))
