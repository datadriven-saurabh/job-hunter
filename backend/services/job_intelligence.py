"""Evidence-only immigration signals and source timestamps, never inferred from ads."""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import re
from urllib.parse import urlparse

SOURCE_HOSTS={'stepstone.de':'StepStone','linkedin.com':'LinkedIn','remoteok.com':'Remote OK','weworkremotely.com':'We Work Remotely','remotive.com':'Remotive','arbeitnow.com':'Arbeitnow','arbeitnow.co.uk':'Arbeitnow UK','greenhouse.io':'Greenhouse','lever.co':'Lever','ashbyhq.com':'Ashby','smartrecruiters.com':'SmartRecruiters','workable.com':'Workable','hiringcafe.com':'HiringCafe','hiring.cafe':'HiringCafe'}
SOURCE_HOSTS.update({'relocate.me':'Relocate.me','berlinstartupjobs.com':'Berlin Startup Jobs','eu-startups.com':'EU-Startups','jobfluent.com':'JobFluent','jobs.hvcapital.com':'HV Capital','jobs.earlybird.com':'Earlybird VC','jobs.pointnine.com':'Point Nine Capital','workingnomads.com':'Working Nomads','wellfound.com':'Wellfound','builtin.com':'Built In','ycombinator.com':'Y Combinator','news.ycombinator.com':'Hacker News'})


def source_name(url):
    host=urlparse(url or '').hostname or ''
    return next((SOURCE_HOSTS[domain] for domain in sorted(SOURCE_HOSTS,key=len,reverse=True) if host==domain or host.endswith('.'+domain)),'Manual import')


def posting_time(value):
    if value is None or value=='':return None,None
    try:
        if isinstance(value,(int,float)) or str(value).isdigit():
            epoch=float(value);epoch=epoch/1000 if epoch>100000000000 else epoch
            parsed=datetime.fromtimestamp(epoch,tz=timezone.utc);precision='time'
        else:
            raw=str(value).strip();precision='date' if re.fullmatch(r'\d{4}-\d{2}-\d{2}',raw) else 'time'
            try:parsed=datetime.fromisoformat(raw.replace('Z','+00:00'))
            except ValueError:parsed=parsedate_to_datetime(raw)
            if parsed.tzinfo is None:
                # Do not invent an exact time zone for a naive source date/time.
                precision='date';parsed=parsed.replace(hour=0,minute=0,second=0,tzinfo=timezone.utc)
        if parsed.year<2000 or parsed>datetime.now(timezone.utc):return None,None
        return parsed.astimezone(timezone.utc).isoformat(),precision
    except (ValueError,TypeError,OverflowError,OSError):return None,None


def visa_signal(text,source_url=''):
    sentences=[s.strip() for s in re.split(r'(?<=[.!?])\s+|\n+',text) if s.strip()]
    yes=[];no=[]
    for sentence in sentences:
        low=sentence.lower()
        if re.search(r'(?:no|without|not (?:offer|provide|available)|cannot|can\W?t|unable to|do not|does not|will not).{0,45}(?:visa|work permit|immigration|sponsor)|(?:visa|work permit|immigration|sponsorship).{0,35}(?:not available|unavailable|not provided|not supported)|must (?:already )?(?:have|hold).{0,40}(?:work authori[sz]ation|right to work)',low):no.append(sentence)
        elif re.search(r'(?:we (?:can |will )?(?:offer|provide|support)|(?:visa|work permit) sponsorship (?:is )?(?:available|provided|offered)|immigration (?:support|assistance) (?:is )?(?:available|provided))',low) and re.search(r'visa|work permit|immigration',low):yes.append(sentence)
    conflict=bool(yes and no)
    status='unknown' if conflict else 'explicit_no' if no else 'explicit_yes' if yes else 'unknown'
    evidence=(no+yes)[:3]
    return {'visa_status':status,'visa_evidence':evidence,'visa_source':source_url if evidence else None,'visa_confidence':0 if not evidence or conflict else 1,'visa_conflict':conflict,'visa_note':'Conflicting sponsorship statements; confirm with the employer.' if conflict else 'No explicit immigration sponsorship statement found.' if not evidence else 'Based on the quoted posting, not a guarantee for this candidate.'}


def language_requirements(text):
    result=[]
    for sentence in re.split(r'(?<=[.!?])\s+|\n+|;|\bbut\b|\band\s+(?=(?:English|German|French|Dutch|Spanish|Italian|Hindi)\b)',text,flags=re.I):
        for language in ['English','German','French','Dutch','Spanish','Italian','Hindi']:
            if not re.search(r'\b'+language+r'\b',sentence,re.I):continue
            if re.search(r'not (?:required|necessary|needed)|no .{0,25}(?:required|necessary)|without .{0,25}knowledge',sentence,re.I):continue
            if re.search(r'preferred|nice.to.have|bonus|advantage|optional',sentence,re.I):importance='preferred'
            elif re.search(r'required|mandatory|must|fluent|fluency|native|C[12]|B[12]',sentence,re.I):importance='required'
            else:continue
            level=re.search(r'\b[ABC][12]\b',sentence,re.I)
            result.append({'language':language,'importance':importance,'level':level.group(0).upper() if level else None,'evidence':sentence.strip()})
    return result


def language_eligibility(requirements,profile):
    levels={'beginner':1,'a1':1,'a2':2,'basic':2,'b1':3,'intermediate':3,'b2':4,'professional':5,'c1':5,'c2':6,'native':6,'fluent':6,'full professional':6}
    supplied={p['language'].casefold():p['level'].casefold() for p in profile.get('base_resume',{}).get('languages',[])}
    missing=[];unknown=[]
    for r in requirements:
        if r['importance']!='required':continue
        value=supplied.get(r['language'].casefold())
        if not value:unknown.append(r['language']);continue
        if value in {'none','not spoken'} or levels.get(value,0)<levels.get((r['level'] or 'professional').lower(),5):missing.append(r['language'])
    return {'eligible':False if missing else None if unknown else True,'missing':missing,'unknown':unknown}


def enrich(job,previous=None,now=None):
    previous=previous or {};out=dict(job);now=now or datetime.now(timezone.utc)
    out['source']=job.get('source') or source_name(job.get('job_url',''))
    out['source_url']=job.get('source_url') or job.get('job_url','')
    posted,precision=posting_time(job.get('posted_at'))
    out['posted_at']=posted;out['posted_at_precision']=job.get('posted_at_precision') or precision
    out['first_seen_at']=previous.get('first_seen_at') or job.get('first_seen_at') or job.get('created_at') or now.isoformat()
    out['last_seen_at']=now.isoformat()
    out['requisition_id']=job.get('requisition_id') or extract_requisition(job.get('description',''))
    out.update(visa_signal(job.get('description',''),out['source_url']))
    out['language_requirements']=language_requirements(job.get('description',''))
    from backend.services.posting_language import posting_language
    out['posting_language']=posting_language(job.get('description',''),job.get('source_language'))
    return out


def extract_requisition(text):
    match=re.search(r'\b(?:job\s*(?:id|number)|req(?:uisition)?\s*(?:id|number|#|no\.?))\s*[:#-]?\s*([A-Z0-9][A-Z0-9_-]{2,50})\b',text,re.I)
    return match.group(1) if match else None


def ranking(job,profile,fit,config,now=None):
    now=now or datetime.now(timezone.utc)
    posted,precision=posting_time(job.get('posted_at'))
    age=max(0,(now-datetime.fromisoformat(posted)).total_seconds()/86400) if posted else None
    fresh=config['freshness'];fresh_score=1 if age is not None and age<=fresh['preferred_days'] else .5 if age is None else max(0,1-age/fresh['maximum_days'])
    source=job.get('source','');quality=.95 if source in {'Greenhouse','Lever','Ashby','SmartRecruiters','Workable'} else .85 if source=='LinkedIn' else .6
    weights=config['priority_weights'];priority=round(fit*weights['fit']+100*fresh_score*weights['freshness']+100*quality*weights['source'],1)
    language=language_eligibility(job.get('language_requirements',language_requirements(job.get('description',''))),profile)
    decision='HIGH_PRIORITY' if priority>=80 else 'APPLY' if priority>=65 else 'LOW_PRIORITY'
    if age is not None and age>fresh['maximum_days']:decision='LOW_PRIORITY'
    if language['eligible'] is None or job.get('visa_conflict'):decision='REVIEW'
    if language['eligible'] is False:decision='REJECTED'
    return {'score':priority,'decision':decision,'age_days':round(age,1) if age is not None else None,'freshness':'Unknown posting date' if age is None else 'Recently posted' if age<=fresh['preferred_days'] else 'Older posting' if age>fresh['maximum_days'] else 'Within search window','source_quality':quality,'language_eligibility':language,'method':'80% profile fit, 15% freshness, 5% source quality; language constraints take precedence. Sponsorship is shown separately, never assumed.'}
