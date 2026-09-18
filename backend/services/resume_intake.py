"""Local, conservative resume intake. Missing facts remain editable blanks."""
import copy
import re
from datetime import datetime
from backend import database as db
from backend.services.job_matching import affirmed_skills

MONTHS={name:i for i,name in enumerate(['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'],1)}
DATE=r'(?:\d{4}-(?:0[1-9]|1[0-2])|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?\s+\d{4})'
RANGE=re.compile(r'('+DATE+r')\s*(?:[-–—]|to)\s*('+DATE+r'|Present|Current|Now)',re.I)
SECTIONS={'summary':'summary','professional summary':'summary','profile':'summary','about me':'summary','experience':'experience','work experience':'experience','professional experience':'experience','employment history':'experience','education':'education','academic background':'education','skills':'skills','technical skills':'skills','core skills':'skills','certifications':'certifications','certificates':'certifications','languages':'languages','projects':'projects'}
ROLE_WORDS=re.compile(r'\b(?:analyst|engineer|developer|manager|consultant|scientist|architect|specialist|lead|director|associate|intern|administrator|designer|owner|founder)\b',re.I)

def month(value):
    if value.casefold() in {'present','current','now'}:return 'Present'
    if re.fullmatch(r'\d{4}-\d{2}',value):return value
    match=re.search(r'([A-Za-z]+)\.?\s+(\d{4})',value)
    return f'{match[2]}-{MONTHS[match[1][:3].lower()]:02d}'

def suggest_titles(profile):
    skills=set(profile['base_resume']['structured_skills'])
    rules=[('Analytics Engineer',{'SQL','dbt','Data modelling','Snowflake','BigQuery'},3),
           ('Data Analyst',{'SQL','Excel','Tableau','Power BI','Statistics','Dashboards','Python'},2),
           ('Business Analyst',{'Requirements analysis','Stakeholder collaboration','Business intelligence','Excel','SQL'},2),
           ('Data Engineer',{'Python','SQL','ETL','Airflow','Spark','Databricks'},3),
           ('Frontend Engineer',{'React','TypeScript','JavaScript','CSS','HTML'},3),
           ('Backend Engineer',{'Python','Java','Go','PostgreSQL','Node.js'},2),
           ('Machine Learning Engineer',{'Machine learning','Python','Statistics','Spark'},3)]
    rows=[{'title':title,'evidence':sorted(skills&needed),'reason':'Supported by skills found in the resume.'} for title,needed,minimum in rules if len(skills&needed)>=minimum]
    return sorted(rows,key=lambda row:-len(row['evidence']))[:5]

def profile_draft(raw,existing=None,resume_id=''):
    lines=[re.sub(r'^\s*[•●▪*]\s*','',line).strip() for line in raw.splitlines() if line.strip()]
    blank={'user_id':'local','personal_details':{key:'' for key in ['full_name','email','phone','location','work_authorization','linkedin_url','github_url','portfolio_url']},'base_resume':{'raw_text':'','structured_skills':[],'experience_history':[],'education':[],'certifications':[],'languages':[],'story_bank':[]},'eeo_demographics':None}
    profile=copy.deepcopy(existing or blank);profile['_revision']=db.profile_revision(existing)
    personal=profile['personal_details'];base=profile['base_resume'];sections={'header':[]};section='header'
    for line in lines:
        key=line.strip(': ').casefold()
        if key in SECTIONS:section=SECTIONS[key];sections.setdefault(section,[])
        else:sections.setdefault(section,[]).append(line)
    header='\n'.join(sections['header'])
    for key,label in [('full_name','(?:full )?name'),('location','(?:location|address)'),('work_authorization','work authori[sz]ation')]:
        match=re.search(r'^'+label+r'\s*:\s*(.+)$',header,re.I|re.M)
        if match:personal[key]=match[1].strip()
    if not re.search(r'^(?:full )?name\s*:',header,re.I|re.M) and lines:
        candidate=lines[0]
        if 2<=len(candidate.split())<=5 and re.fullmatch(r'[^\W\d_]+(?:[ .’\'-]+[^\W\d_]+)+',candidate,re.UNICODE) and not re.search(r'engineer|analyst|resume|curriculum|developer|manager|scientist',candidate,re.I):personal['full_name']=candidate
    email=re.search(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',header)
    if email:personal['email']=email[0]
    phone=re.search(r'(?<!\w)(\+?\d[\d ()-]{8,}\d)(?!\w)',header)
    if phone and 9<=len(re.sub(r'\D','',phone[1]))<=15 and not RANGE.search(phone[1]):personal['phone']=phone[1].strip()
    for field,host in [('linkedin_url','linkedin.com/in/'),('github_url','github.com/')]:
        match=re.search(r'(?:https?://)?(?:www\.)?'+re.escape(host)+r'[^\s|,]+',header,re.I)
        if match:personal[field]=match[0] if match[0].startswith('http') else 'https://'+match[0]
    if sections.get('summary'):base['raw_text']=' '.join(sections['summary'])
    skills=sorted(affirmed_skills(raw))
    if skills:base['structured_skills']=skills
    experiences=[];pending=[];current=None;ambiguous=False
    for line in sections.get('experience',[]):
        match=RANGE.search(line)
        if match:
            prefix=line[:match.start()].strip(' |,–—-');parts=[v.strip() for v in re.split(r'\s*[|]\s*|\s+at\s+',prefix) if v.strip()]
            if len(parts)<2 and len(pending)>=2 and all(len(value)<=100 and not value.endswith('.') for value in pending[-2:]):
                parts=pending[-2:]+parts
            if len(parts)>=2:
                first,second=parts[-2:]
                role,company=(second,first) if ROLE_WORDS.search(second) and not ROLE_WORDS.search(first) else (first,second)
                current={'role':role,'company':company,'start_date':month(match[1]),'end_date':month(match[2]),'bullet_points':[],'achievements':[],'location':''}
                experiences.append(current)
            else:current=None;ambiguous=True
            pending=[]
        else:
            pending.append(line)
            if current:current['bullet_points'].append(line.lstrip('- '))
    # A role/company header immediately before the next date belongs to that role.
    for previous,nxt in zip(experiences,experiences[1:]):
        previous['bullet_points']=[line for line in previous['bullet_points'] if line not in {nxt['company'],nxt['role'],nxt['role']+' | '+nxt['company']}]
    if experiences:base['experience_history']=experiences
    education=[]
    for line in sections.get('education',[]):
        parts=[v.strip() for v in line.split('|')];year=re.search(r'\b(19\d{2}|20\d{2})\b',parts[-1])
        if len(parts)>=3 and year and int(year[1])<=datetime.now().year+10:
            education.append({'institution':parts[0],'degree':parts[1],'field_of_study':parts[2] if len(parts)>3 else '', 'graduation_year':year[1]})
    if education:base['education']=education
    if sections.get('certifications'):base['certifications']=sections['certifications'][:30]
    missing=[key.replace('_',' ') for key in ['full_name','email','phone','location','work_authorization'] if not personal.get(key)]
    warnings=['Review the extracted draft before saving. Nothing is inferred about work authorization, demographics, or achievement verification.']
    if existing:warnings.append('Fields not found in this file retain your existing saved facts. Parsed work history replaces the history in this draft only.')
    if sections.get('experience') and not experiences:warnings.append('Work history could not be parsed confidently. Add roles and exact month/year dates manually.')
    elif ambiguous:warnings.append('At least one work-history entry was ambiguous and was left out. Review roles, companies, and dates manually.')
    if sections.get('education') and not education:warnings.append('Review education manually; the parser could not separate institution, degree and year.')
    if not base.get('raw_text'):missing.append('professional summary')
    return {'profile':profile,'resume_id':resume_id,'suggested_titles':suggest_titles(profile),'missing_fields':missing,'warnings':warnings,'review_required':True,'saved':False,'method':'Local text and section parsing; no external model or upload.'}
