import hashlib
import re

def fingerprint(job):
    normalize=lambda value:re.sub(r'\s+',' ',str(value).casefold()).strip()
    return hashlib.sha256('\n'.join(normalize(job.get(k,'')) for k in ['company_name','job_title','location','description']).encode()).hexdigest()

def quality(job):
    return 3 if job.get('source') in {'Greenhouse','Lever','Ashby','SmartRecruiters','Workable'} else 2 if job.get('source')=='LinkedIn' else 1
