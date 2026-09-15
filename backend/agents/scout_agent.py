import hashlib
import math
import re
import httpx
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

def score(job, profile, criteria):
    from backend.services.job_matching import assess, exclusions
    if exclusions(job,criteria):return None
    return assess(job,profile,criteria)['score']/100

def fetch_feed(provider, board):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', board): raise ValueError('Use a board slug, not a URL.')
    from backend.agents.job_sources import public_get
    if provider == 'greenhouse':
        response = public_get(f'https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true')
        response.raise_for_status()
        return [{'company_name':board, 'posted_at':j.get('first_published'),'last_updated_at':j.get('updated_at'),'requisition_id':str(j['id']), 'job_title':j['title'], 'job_url':j['absolute_url'], 'description':re.sub('<[^>]+>', ' ',j.get('content','')), 'location':j.get('location',{}).get('name',''), 'employment_type':'Full-time'} for j in response.json()['jobs']]
    if provider == 'lever':
        response = public_get(f'https://api.lever.co/v0/postings/{board}?mode=json')
        response.raise_for_status()
        return [{'company_name':board, 'posted_at':j.get('createdAt'),'requisition_id':j.get('id'), 'job_title':j['text'], 'job_url':j['hostedUrl'], 'description':j.get('descriptionPlain',''), 'location':j.get('categories',{}).get('location',''), 'employment_type':j.get('categories',{}).get('commitment','Full-time')} for j in response.json()]
    raise ValueError('Supported feeds: greenhouse and lever.')

def job_id(url):
    parsed=urlparse(url)
    host=parsed.netloc.lower()
    if host.endswith('linkedin.com'):
        match=re.search(r'(\d+)$',parsed.path.rstrip('/'))
        if match:url='https://www.linkedin.com/jobs/view/'+match.group(1)
    else:
        query=[(k,v) for k,v in parse_qsl(parsed.query) if not k.lower().startswith(('utm_','ref','source','tracking'))]
        url=urlunparse((parsed.scheme.lower(),host,parsed.path.rstrip('/'),'',urlencode(sorted(query)),''))
    return hashlib.sha256(url.encode()).hexdigest()[:20]
