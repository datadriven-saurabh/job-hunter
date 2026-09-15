"""Unified generation: models select/cite evidence; code validates and renders facts."""
import copy
import ipaddress
import re
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse
from typing import Literal
from pydantic import BaseModel,Field,ConfigDict
from schemas import UserProfile
from backend.prompts import build_prompt,RESUME_FORMAT,PROMPT_VERSIONS
from backend.ai.router import ModelRouter,ModelUnavailable,digest
from backend.services.job_matching import detected,affirmed_skills
from backend.services.onepage import joined_bullets
from backend.services.job_intelligence import enrich
from backend.services.career_validation import Validation,words,clean_text,validate_ats,validate_xyz,source_span,check_facts,validate_referral


class StrictModel(BaseModel):model_config=ConfigDict(extra='forbid')
class Strategy(StrictModel):
    priority_keywords:list[str]=Field(default_factory=list,max_length=30)
    source_ids:list[str]=Field(default_factory=list,max_length=24)
    do_not_claim:list[str]=Field(default_factory=list,max_length=30)
class XYZ(StrictModel):
    source_id:str
    outcome:str=Field(max_length=500)
    measurement:str=Field(max_length=300)
    method:str=Field(max_length=700)
class XYZOutput(StrictModel):bullets:list[XYZ]=Field(default_factory=list,max_length=24)
class Selection(StrictModel):source_ids:list[str]=Field(default_factory=list,max_length=20)


def candidate(raw):
    if isinstance(raw,str):
        from backend.services.profile_intake import parse_raw_profile
        return parse_raw_profile(raw)
    return UserProfile.model_validate(raw).model_dump()


def context(raw_profile,target):
    profile=candidate(raw_profile);job=enrich(target)
    if not job.get('job_title') or not job.get('company_name') or len(job.get('description','').strip())<80:raise ValueError('Provide the exact title, company and at least 80 characters of job description.')
    registry={};entries=[]
    for i,e in enumerate(profile['base_resume']['experience_history']):
        for n,b in enumerate(joined_bullets(e['bullet_points'])):
            key=f'experience.{i}.bullet.{n}';registry[key]=clean_text(b);entries.append({'source_id':key,'text':clean_text(b),'role_index':i,'company':e['company']})
        for n,a in enumerate(e.get('achievements',[])):
            if a['verified']:
                key=f'experience.{i}.achievement.{n}'
                text=xyz_text(a);registry[key]=text;entries.append({'source_id':key,'text':text,'role_index':i,'company':e['company'],'xyz':a})
    deduplicated={}
    for entry in entries:deduplicated[(entry['role_index'],entry['text'].casefold())]=entry
    entries=list(deduplicated.values())
    full='\n'.join([profile['base_resume']['raw_text'],'\n'.join(profile['base_resume']['structured_skills'])]+list(registry.values()))
    skills=sorted(detected(job['job_title']+' '+job['description'])&affirmed_skills(full))
    wanted=detected(job['description']);entries.sort(key=lambda e:-len(detected(e['text'])&wanted))
    return {'profile':profile,'job':job,'registry':registry,'entries':entries,'skills':skills}


def xyz_text(a):
    outcome=clean_text(a['outcome']).rstrip('.,;')
    measurement=clean_text(a['measurement']).rstrip('.,;')
    method=clean_text(a['method']).rstrip('.,;')
    method=re.sub(r'^by\s+','',method,flags=re.I)
    if re.match(r'^(on|with)\s+',method,re.I):method='using '+re.sub(r'^(on|with)\s+','',method,flags=re.I)
    return f'{outcome}, as measured by {measurement}, by {method}.'


def rule_xyz(entry):
    if entry.get('xyz'):return {k:entry['xyz'][k] for k in ['outcome','measurement','method']}
    source=entry['text'].rstrip('.')
    m=re.match(r'(.+?), as measured by (.+?), by (.+)$',source,re.I)
    if not m:m=re.match(r'((?:Reduced|Increased|Improved|Cut|Optimized|Optimised) .+?) by (\d[^,]*?),? by (.+)$',source,re.I)
    if m:return dict(zip(['outcome','measurement','method'],m.groups()))
    return None


def output(asset_type,text,check,ctx,*,data=None,missing=None,router=None):
    report=check.result(text)
    return {'asset_type':asset_type,'status':'valid' if report['valid'] and not missing else 'needs_user_input',
            'text':text if report['valid'] else '', 'preview':text,
            'validation':report,'missing_inputs':missing or [],'data':data or {},
            'evidence':[{'source_id':e['source_id'],'text':e['text'],'company':e['company']} for e in ctx['entries']],
            'prompt_versions':dict(PROMPT_VERSIONS),'template':RESUME_FORMAT,
            'generation_method':'Evidence-constrained selection and deterministic rendering',
            'model_usage':router.events if router else []}


def generateATSResume(userProfile,targetJD,customFormat=None,router=None):
    ctx=context(userProfile,targetJD);router=router or ModelRouter();check=Validation();p=ctx['profile'];resume=p['base_resume']
    by_id={e['source_id']:e for e in ctx['entries']};allowed_skills=set(ctx['skills']);strategy=None
    try:
        prompt=build_prompt('resume_strategy',p,ctx['job'],customFormat,{'evidence':ctx['entries'],'allowed_keywords':ctx['skills'],'task':'Select existing source IDs and supported priority keywords. Do not write claims.'})
        def validate_strategy(result):
            if not set(result.source_ids)<=by_id.keys() or not set(result.priority_keywords)<=allowed_skills:raise ValueError('Unsupported strategy references')
        strategy=router.run('resume_strategy',prompt,Strategy,validator=validate_strategy)
    except ModelUnavailable:pass
    entries=ctx['entries']
    if strategy and strategy.source_ids:
        order={key:i for i,key in enumerate(strategy.source_ids)};entries=sorted(entries,key=lambda e:order.get(e['source_id'],999))
    xyz={e['source_id']:rule_xyz(e) for e in entries if rule_xyz(e)}
    unresolved=[e for e in entries if e['source_id'] not in xyz]
    if unresolved:
        try:
            prompt=build_prompt('resume_writing',p,ctx['job'],customFormat,{'approved_strategy':strategy.model_dump() if strategy else {'source_ids':list(by_id),'priority_keywords':ctx['skills']},'evidence':unresolved,'task':'Extract XYZ clauses only. Each outcome, measurement and method must be an exact contiguous substring of the SAME cited evidence. Outcome starts with its original action verb. Measurement includes its original metric. Never approximate, reassign a number, or invent a method. Omit bullets that lack evidence.'})
            def validate_extraction(result):
                for a in result.bullets:
                    if a.source_id not in by_id:raise ValueError('Unknown source')
                    source=by_id[a.source_id]['text']
                    if any(not source_span(getattr(a,k),source) for k in ['outcome','measurement','method']):raise ValueError('Non-source claim')
                    if validate_xyz(a.model_dump()).errors:raise ValueError('Incomplete XYZ')
            result=router.run('resume_writing',prompt,XYZOutput,validator=validate_extraction)
            for a in result.bullets:xyz[a.source_id]=a.model_dump(exclude={'source_id'})
        except ModelUnavailable:pass
    selected=[];missing=[]
    for i,e in sorted(enumerate(resume['experience_history']),key=lambda item:item[1]['start_date'],reverse=True):
        bullets=[]
        for entry in entries:
            if entry['role_index']!=i or entry['source_id'] not in xyz:continue
            item=xyz[entry['source_id']]
            if validate_xyz(item).errors:continue
            text=xyz_text(item)
            if text not in [b['text'] for b in bullets]:bullets.append({'text':text,'source_id':entry['source_id'],'xyz':item})
        bullets=bullets[:5 if not selected else 3]
        if not bullets:
            missing.append(f'Add verified XYZ achievements for {e["role"]} at {e["company"]}: outcome, actual metric, and method.')
        selected.append({**e,'bullets':bullets})
    personal=p['personal_details'];summary=clean_text(resume['raw_text'])
    check.require(50<=words(summary)<=70,'summary_length','Provide a factual profile summary of 50–70 words.')
    check.require(bool(selected) and all(e['bullets'] for e in selected),'xyz_evidence','Every included role needs a measured outcome and its actual method. Complete the requested evidence before export.')
    header=[personal['full_name'],' | '.join(filter(None,[personal['email'],personal['phone'],personal['location']])), ' | '.join(filter(None,[personal.get('linkedin_url'),personal.get('portfolio_url') or personal.get('github_url')]))]
    lines=['# '+clean_text(header[0]),clean_text(header[1]),clean_text(header[2]),'','## PROFILE',summary,'','## WORK EXPERIENCE']
    for e in selected:
        lines += ['### '+clean_text(e['company'])+' - '+clean_text(e['role']),clean_text(e['start_date']+' - '+e['end_date']+(' | '+e['location'] if e.get('location') else ''))]
        lines += ['* '+b['text'] for b in e['bullets']]
        lines += ['']
    if resume['education']:
        lines+=['## EDUCATION']
        for e in resume['education']:lines += [clean_text(f"{e['institution']} - {e['degree']}, {e['field_of_study']} ({e['graduation_year']})")]
    skills=sorted(resume['structured_skills'],key=lambda s:(not bool(detected(s)&allowed_skills),s.lower()))
    if skills:lines+=['','## SKILLS',clean_text(', '.join(skills))]
    if resume.get('languages'):lines+=['','## LANGUAGE SKILLS',', '.join(clean_text(l['language']+' - '+l['level']) for l in resume['languages'])]
    if resume.get('certifications'):lines+=['','## CERTIFICATIONS']+['* '+clean_text(c) for c in resume['certifications']]
    markdown='\n'.join(lines).strip();check.errors+=validate_ats(markdown).errors
    data={'personal':personal,'summary':summary,'experience':selected,'education':resume['education'],'skills':skills,'certifications':resume.get('certifications',[]),'languages':resume.get('languages',[]),'format':RESUME_FORMAT,'custom_format_applied':False}
    if customFormat:check.warnings.append('Custom preferences were recorded; the required reference template remains selected.')
    return output('resume',markdown,check,ctx,data=data,missing=missing,router=router)


def _ranked_evidence(ctx,router,task,extra=None):
    entries=ctx['entries']
    try:
        prompt=build_prompt(task,ctx['profile'],ctx['job'],extra={'evidence':entries,'task':'Choose the most relevant supplied source IDs, in order. Return IDs only; prose is rendered from those verified sources.',**(extra or {})})
        def valid(result):
            if not set(result.source_ids)<={e['source_id'] for e in entries}:raise ValueError('Unsupported evidence')
        result=router.run('outreach' if task=='cover_letter' else 'application_answer',prompt,Selection,validator=valid)
        by_id={e['source_id']:e for e in entries}
        if result.source_ids:return [by_id[k] for k in dict.fromkeys(result.source_ids)]
    except ModelUnavailable:pass
    return entries


def generateCoverLetter(userProfile,targetJD,router=None,recipient=''):
    ctx=context(userProfile,targetJD);router=router or ModelRouter();check=Validation();p=ctx['profile']['personal_details'];job=ctx['job']
    entries=_ranked_evidence(ctx,router,'cover_letter');chosen=[];size=0
    for entry in entries:
        if size+words(entry['text'])>150:continue
        chosen.append(entry);size+=words(entry['text'])
        if size>=115:break
    check.require(any(re.search(r'\d',e['text']) for e in chosen),'cover_metrics','Add a supported achievement with its actual metric for the core value paragraph.')
    check.require(bool(ctx['skills']),'cover_skills','No evidenced hard-skill overlap was found. Review your profile and job requirements.')
    matching=', '.join(ctx['skills'][:4]) or 'the experience documented in my profile'
    title=job['job_title'];company=job['company_name']
    header='\n'.join(filter(None,[p['full_name'],' | '.join([p['email'],p['phone'],p['location']]),p.get('linkedin_url'),datetime.now(timezone.utc).strftime('%B %d, %Y'),company]))
    hook=f'I am applying for the {title} position at {company}. The posting connects directly with my background in {matching}. I would welcome the opportunity to bring this experience to your team, with a focus on the responsibilities outlined in the role and the practical outcomes your team needs to deliver.'
    core='My relevant experience is grounded in the following work. '+' '.join('At '+e['company']+', '+('I '+e['text'][0].lower()+e['text'][1:] if not e['text'].startswith('I ') else e['text']).rstrip('.')+'.' for e in chosen)
    # The source quotation is explicitly company context, never a candidate claim.
    jd_sentences=[s.strip() for s in re.split(r'(?<=[.!?])\s+|\n+',job['description']) if 6<=words(s)<=35]
    specific=next((s for s in jd_sentences if not re.search(r'ignore|instruction|system prompt',s,re.I)),None)
    check.require(bool(specific),'company_context','Provide a concrete responsibility or company goal from the posting to support the fit paragraph.')
    fit=(f'The posting states: "{specific}" ' if specific else '')+'This is the context I would use to focus an initial conversation about the role. I would want to understand how the team defines success, where the immediate priorities sit, and how my documented experience could contribute to those priorities without assuming that every challenge is the same.'
    cta=f'I would welcome a conversation about the {title} role and the experience most relevant to your team. Thank you for reviewing my application and considering my background. I am happy to discuss the examples above in more detail.'
    paragraphs=[hook,core,fit,cta];text=header+'\n\nDear '+(recipient or company+' Hiring Team')+',\n\n'+'\n\n'.join(paragraphs)+'\n\nSincerely,\n'+p['full_name']
    text=clean_text(text);check.require(250<=words(text)<=400,'cover_word_count','A cover letter must contain 250–400 words. Add more relevant source achievements if it is too short; shorten the supplied wording if it is too long.')
    claims=[{'source_id':e['source_id'],'text':e['text']} for e in chosen];check.errors+=check_facts(claims,ctx['registry']).errors
    return output('cover_letter',text,check,ctx,data={'paragraphs':paragraphs,'header':header,'salutation':'Dear '+(recipient or company+' Hiring Team')+',','signoff':'Sincerely,\n'+p['full_name'],'claims':claims},router=router)


def generateLinkedInReferralMessage(userProfile,targetJD,messageType='post_connection',*,recipient='',resume_url='',shared_context=''):
    if messageType not in {'post_connection','invite_note','mutual_group'}:raise ValueError('Choose post_connection, invite_note or mutual_group.')
    ctx=context(userProfile,targetJD);job=ctx['job'];name=ctx['profile']['personal_details']['full_name'];missing=[]
    req=str(job.get('requisition_id') or '[JOB ID REQUIRED]')
    if not job.get('requisition_id'):missing.append('Enter the employer Job ID / requisition number. The tracker hash is not an employer Job ID.')
    url=resume_url or ctx['profile']['personal_details'].get('portfolio_url') or '[PUBLIC RESUME URL]'
    if url=='[PUBLIC RESUME URL]':missing.append('Provide a public resume or portfolio URL that you have chosen to share.')
    else:
        parsed=urlparse(url)
        private=False
        try:private=not ipaddress.ip_address(parsed.hostname or '').is_global
        except ValueError:pass
        if private or parsed.scheme!='https' or not parsed.hostname or parsed.hostname in {'localhost','127.0.0.1','::1'} or parsed.username:raise ValueError('Use a public HTTPS resume or portfolio URL. Local download links cannot be shared with a referrer.')
    skills=ctx['skills'][:2];skill_text=', '.join(skills) or '[VERIFIED SKILL REQUIRED]';company=job['company_name'];title=job['job_title'];hello='Hi '+(recipient.strip().split()[0] if recipient.strip() else 'there')+','
    if messageType=='invite_note':
        text=f'{hello} I am applying for {title} at {company} (Job ID: {req}). My skills include {skill_text}. If you feel comfortable, could you consider a referral? Resume: {url}'
    else:
        opening='Thanks for connecting.'
        if messageType=='mutual_group':
            if not shared_context:missing.append('Confirm the actual shared group, university or mutual connection; shared context is never assumed.')
            opening='I am reaching out through '+(shared_context or '[CONFIRMED SHARED CONTEXT]')+'.'
        text=f'{hello} {opening} I am applying for the {title} position at {company} (Job ID: {req}) and wanted to make it easy to review the opportunity.\n\nMy profile includes {skill_text}, which the job description also mentions. You can review my resume or portfolio here: {url}. I would be happy to clarify the experience most relevant to the role.\n\nIf you feel comfortable, would you consider a referral? No pressure if you are unable to help. Thank you for your time. Best, {name}'
    text=clean_text(text);check=validate_referral(text,messageType,title,req,url,skills)
    return output(messageType,text,check,ctx,missing=missing,data={'requisition_id':req,'resume_url':url,'skills':skills,'requires_link_review':True})


# Python-style names for internal callers; public names mirror the supplied interface.
generate_ats_resume=generateATSResume
generate_cover_letter=generateCoverLetter
generate_referral=generateLinkedInReferralMessage
