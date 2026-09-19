"""Explainable job-priority heuristic based only on supplied professional facts.

Not an interview probability, semantic model, or verification of eligibility.
"""
import re
from datetime import date, datetime, timezone

SKILLS={
 'Databricks':['databricks'], 'Microsoft Fabric':['microsoft fabric'], 'Data governance':['data governance','data catalogues','data catalogs'],
 'SQL':['sql','mysql','postgresql','postgres','t-sql'], 'Python':['python'],
 'Power BI':['power bi','powerbi'], 'Tableau':['tableau'], 'Apache Superset':['apache superset','superset'],
 'Metabase':['metabase'], 'ClickHouse':['clickhouse'], 'Airbyte':['airbyte'], 'dbt':['dbt'],
 'Snowflake':['snowflake'], 'BigQuery':['bigquery','big query'], 'Redshift':['redshift'],
 'Excel':['excel','microsoft excel'], 'ETL':['etl','elt','data pipelines','data pipeline'],
 'Data modelling':['data modelling','data modeling','dimensional modelling','dimensional modeling','star schema'],
 'Business intelligence':['business intelligence','bi platforms','bi platform','bi dashboards'],
 'Dashboards':['dashboard','dashboards','reporting'], 'Statistics':['statistics','statistical'],
 'Experimentation':['a/b testing','ab testing','experimentation','hypothesis testing'],
 'Product analytics':['product analytics','amplitude','mixpanel','product analysis'],
 'Stakeholder collaboration':['stakeholder','stakeholders','cross-functional'],
 'Requirements analysis':['requirements gathering','business requirements','prds','prd','requirements analysis'],
 'Git':['git','github','gitlab','git/github'], 'Docker':['docker'], 'Airflow':['airflow'],
 'Spark':['spark','pyspark'], 'AWS':['aws','amazon web services'], 'Azure':['azure'],
 'GCP':['gcp','google cloud'], 'MongoDB':['mongodb'], 'Machine learning':['machine learning'],
 'React':['react','reactjs','react.js'], 'TypeScript':['typescript'], 'JavaScript':['javascript'],
 'Java':['java'], 'Go':['golang','go programming'], 'Rust':['rust'], 'Kubernetes':['kubernetes','k8s'],
 'Node.js':['node.js','nodejs'], 'PostgreSQL':['postgresql','postgres'],
 'CSS':['css'], 'HTML':['html'], 'Figma':['figma'], 'Salesforce':['salesforce'],
 'SAP':['sap'], 'Financial analysis':['financial analysis','financial modelling','financial modeling'],
}

def contains(text, term):
    return bool(re.search(r'(?<!\w)'+re.escape(term.lower())+r'(?!\w)',text.lower()))

def detected(text):
    return {skill for skill,aliases in SKILLS.items() if any(contains(text,a) for a in aliases)}

def affirmed_skills(text):
    """Conservatively omit negated/aspirational clauses from candidate evidence."""
    clauses=re.split(r'\n|(?<=[.!?])\s+|\bbut\b|;',text,flags=re.I)
    return set().union(*(detected(c) for c in clauses if not re.search(r"\b(?:not(?! only)|never|no experience|without experience|haven.t|have not|want to learn|plan to learn|interested in learning|currently learning|am learning|beginner in|no knowledge|lack of experience)\b",c,re.I)))


def family(title):
    t=title.lower()
    if re.search(r'analytics? engineer',t):return 'analytics engineering'
    if re.search(r'(data|product|business|bi|reporting|insights|business intelligence).*analyst|business intelligence',t):return 'analytics'
    if re.search(r'data engineer',t):return 'data engineering'
    if re.search(r'data scien|machine learning',t):return 'data science'
    if re.search(r'software|frontend|front.end|backend|back.end|full.stack|developer',t):return 'software'
    return t.strip()

def title_fit(title, targets):
    if not targets:return 50
    if any(contains(title,t) for t in targets):return 100
    f=family(title);fs={family(t) for t in targets}
    if f in fs:return 90
    if f in {'analytics','analytics engineering','data engineering','data science'} and fs & {'analytics','analytics engineering','data engineering','data science'}:return 55
    return 10

def profile_evidence(profile):
    r=profile['base_resume'];items=[]
    for e in r.get('experience_history',[]):
        for bullet in e.get('bullet_points',[]):items.append((e['role']+' at '+e['company'],bullet))
        for a in e.get('achievements',[]):
            if a.get('verified'):items.append((e['role']+' at '+e['company'],' '.join([a['outcome'],a['measurement'],a['method']])))
    items += [('Profile summary',r.get('raw_text','')),('Listed skills',', '.join(r.get('structured_skills',[])))]
    return items

def experience_years(profile):
    months=set();today=date.today();now=today.year*12+today.month-1
    for e in profile['base_resume'].get('experience_history',[]):
        try:
            y,m=map(int,e['start_date'].split('-'));start=y*12+m-1
            if e['end_date']=='Present':end=now
            else:
                y,m=map(int,e['end_date'].split('-'));end=y*12+m-1
            months.update(range(start,min(end,now)+1))
        except (KeyError,ValueError):continue
    return round(len(months)/12,1)

COUNTRY_ALIASES={
 'germany':('germany','deutschland','de','deu'),
 'india':('india','ind','bharat'),
 'netherlands':('netherlands','nederland','nl','nld'),
 'france':('france','fr','fra'),
 'united kingdom':('united kingdom','uk','great britain','gb','england','scotland','wales','northern ireland'),
 'united states':('united states','united states of america','usa','us'),
}
EU_COUNTRIES=('austria','belgium','bulgaria','croatia','cyprus','czechia','czech republic','denmark','estonia','finland','france','germany','greece','hungary','ireland','italy','latvia','lithuania','luxembourg','malta','netherlands','poland','portugal','romania','slovakia','slovenia','spain','sweden')

def location_matches(location,target):
    """Explicit country aliases only; a city or remote label is not work authorization."""
    target=target.strip().casefold()
    if contains(location,target):return True
    canonical=next((name for name,aliases in COUNTRY_ALIASES.items() if target in aliases),target)
    countries=EU_COUNTRIES if target in {'eu','european union'} else EU_COUNTRIES+('united kingdom','norway','switzerland','iceland','albania','serbia','ukraine','moldova','montenegro','north macedonia','bosnia and herzegovina') if target=='europe' else (canonical,)
    return any(contains(location,alias) for country in countries for alias in COUNTRY_ALIASES.get(country,(country,)))

def exclusions(job, criteria):
    content=job['job_title']+' '+job.get('description','');loc=job.get('location','');reasons=[]
    if any(contains(content,x) for x in criteria.get('dealbreaker_keywords',[])):reasons.append('Excluded keyword')
    if loc and criteria.get('target_locations') and not any(location_matches(loc,x) for x in criteria['target_locations']):reasons.append('Location preference')
    if criteria.get('min_salary_threshold') and job.get('salary_max') and job['salary_max']<criteria['min_salary_threshold']:reasons.append('Salary preference')
    if not all(contains(content,x) for x in criteria.get('required_stack_keywords',[])):reasons.append('Required search keyword')
    kind=job.get('employment_type','')
    if kind.lower() not in {'','not specified','unknown','unspecified'} and criteria.get('employment_types') and kind not in criteria['employment_types']:reasons.append('Employment type')
    max_age=criteria.get('max_posting_age_days')
    if max_age:
        from backend.services.job_intelligence import posting_time
        posted,_=posting_time(job.get('posted_at'))
        if not posted:reasons.append('Posting date unknown (age filter active)')
        elif (datetime.now(timezone.utc)-datetime.fromisoformat(posted)).total_seconds()>max_age*86400:reasons.append(f'Posted more than {max_age} days ago')
    return reasons

def assess(job, profile, criteria):
    jd=job.get('description','');title=job['job_title'];evidence=profile_evidence(profile)
    # Description drives requirements; title alone cannot establish skill coverage.
    def required_mentions(line):
        return {skill for skill in detected(line) if not any(re.search(r'(?<!\w)'+re.escape(alias)+r'(?!\w)\s+(?:is\s+)?not (?:required|needed|necessary)',line,re.I) for alias in SKILLS[skill])}
    lines_with_skills=[(line,required_mentions(line)) for line in re.split(r"\n|(?<=[.!?])\s+|;|\bbut\b",jd)]
    requirements=set().union(*(skills for _,skills in lines_with_skills));available=affirmed_skills('\n'.join(t for _,t in evidence))
    evidence_with_skills=[(source,text,affirmed_skills(text)) for source,text in evidence]
    rows=[]
    for skill in sorted(requirements):
        lines=[line for line,skills in lines_with_skills if skill in skills]
        optional=bool(lines) and all(re.search(r'preferred|nice.to.have|bonus|a plus|desirable',line,re.I) for line in lines)
        required_skill=not optional and any(re.search(r'\bmust\b|\brequired\b|strong (?:expertise|proficiency|knowledge)|essential|is core|proficien',line,re.I) for line in lines)
        proof=next(((source,text) for source,text,skills in evidence_with_skills if skill in skills),None)
        rows.append({'skill':skill,'importance':'preferred' if optional else 'required' if required_skill else 'mentioned','matched':skill in available,
                     'job_evidence':(lines[0] if lines else jd)[:350],
                     'profile_source':proof[0] if proof else None,'profile_evidence':proof[1][:350] if proof else None})
    def importance(row):return {'preferred':.5,'mentioned':1,'required':2}[row['importance']]
    weight=sum(importance(r) for r in rows)
    coverage=100*sum(importance(r) for r in rows if r['matched'])/weight if weight else 0
    role=title_fit(title,criteria.get('target_roles',[]))
    years=experience_years(profile)
    # Only compare clearly general experience requirements, not years in a particular tool.
    matches=re.findall(r'(\d{1,2})(?:\s*[-–]\s*\d{1,2})?\s*\+?\s*years?\s+(?:of\s+)?(?:professional\s+|relevant\s+|total\s+|work\s+)?experience',jd,re.I)
    required=max(map(int,matches)) if matches else None
    seniority=100*min(1,years/required) if required else 50
    warnings=[]
    eligibility=[]
    flat=re.sub(r'\s+',' ',jd)
    professional_text=' '.join(t for _,t in evidence)
    from backend.services.job_intelligence import language_requirements,language_eligibility
    language_rules=language_requirements(jd)
    language_check=language_eligibility(language_rules,profile)
    for language in language_check['missing']+language_check['unknown']:
        eligibility.append('Verify language requirement: '+language+' proficiency is missing or below the stated level.')
    for language,pattern in [('German',r'(?:speak|fluent|fluency|proficien\w*|require\w*).{0,40}German|German.{0,35}(?:required|C1|B2|fluent)|(?:sprichst|Deutschkenntnisse).{0,25}Deutsch|Deutschkenntnisse'),('English C1',r'English.{0,25}C1|C1.{0,25}English')]:
        found=re.search(pattern,flat,re.I)
        if found and not any(r['language']==language.split()[0] for r in language_rules) and not re.search(r'not (?:required|needed|necessary)',found.group(0),re.I) and not contains(professional_text,language):eligibility.append('Verify language requirement: '+found.group(0))
    region=re.search(r'(?:remote|remotely).{0,45}(?:within|only|based in).{0,100}',flat,re.I)
    if region:eligibility.append('Verify permitted work location: '+region.group(0))
    if required:warnings.append(f'{required}+ years mentioned; your dated work history totals about {years} years. Domain-specific experience still needs review.')
    else:warnings.append('No unambiguous general years-of-experience requirement found.')
    limited=bool(job.get('description_incomplete')) or len(jd.split())<35 or len(requirements)<3
    if limited:warnings.append('Limited description or too few recognized requirements: obtain the full posting before prioritising.')
    kind=job.get('employment_type','')
    if kind.lower() in {'','not specified','unknown','unspecified'}:warnings.append('Employment type is not specified; retained for review.')
    if 'remote' in job.get('location','').lower():warnings.append('Remote does not establish worldwide eligibility. Check permitted countries, time zone and work authorization.')
    warnings.append('Work authorization, sponsorship and mandatory credentials are not verified.')
    conflicts=exclusions(job,criteria)
    # Fixed dimensions keep adding unrelated profile skills from depressing the score.
    total=round(.65*coverage+.25*role+.10*seniority)
    if role<=10:total=min(total,49)
    if required and years<required:total=min(total,69)
    if re.search(r'\b(staff|principal|director|head|vp)\b',title,re.I) and not any(re.search(r'\b(staff|principal|director|head|vp)\b',e['role'],re.I) for e in profile['base_resume'].get('experience_history',[])):
        warnings.append('Title indicates a leadership/seniority step beyond your listed titles.');total=min(total,69)
    missing_required=[r['skill'] for r in rows if r['importance']=='required' and not r['matched']]
    if missing_required:
        total=min(total,69)
        warnings.append('Explicitly emphasized requirements without profile evidence: '+', '.join(missing_required))
    if limited or conflicts:total=min(total,49)
    if eligibility:total=min(total,69)
    warnings.extend(eligibility)
    priority='Review details' if limited or conflicts or eligibility else ('Apply first' if total>=75 else 'Consider' if total>=55 else 'Stretch / low fit')
    return {'version':'evidence-v1','score':total,'priority':priority,'confidence':'Limited' if limited else 'Moderate',
            'components':[{'name':'Job skill coverage','score':round(coverage),'weight':65},{'name':'Target role alignment','score':role,'weight':25},{'name':'General experience','score':round(seniority),'weight':10}],
            'matched_skills':[r['skill'] for r in rows if r['matched']], 'missing_skills':[r['skill'] for r in rows if not r['matched']],
            'requirements':rows,'warnings':warnings,'preference_conflicts':conflicts,'profile_years':years,
            'method':'Local rule-based priority index: 65% recognized job skill coverage, 25% target role alignment, 10% general experience. Unknown experience receives 50/100; missing requirements receive no coverage credit. Gaps mean not evidenced in your profile. Not a hiring probability.'}
