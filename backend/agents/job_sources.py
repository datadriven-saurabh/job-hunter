"""Bounded public job discovery. No sessions, credentials, or challenge bypasses."""
import hashlib
import html
import json
import re
import time
from xml.etree import ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode, urljoin, urlparse
import httpx
from bs4 import BeautifulSoup
from backend import database as db
from backend.agents.scout_agent import fetch_feed

SOURCE_INFO=[
 {'id':'arbeitnow','name':'Arbeitnow Europe','kind':'public-search','note':'Free public European jobs API; attribution retained.'},
 {'id':'arbeitnow_uk','name':'Arbeitnow UK','kind':'public-search','note':'Free public UK jobs API; attribution retained.'},
 {'id':'smartrecruiters','name':'SmartRecruiters','kind':'company-board','note':'Public company postings; up to 200 cards and 25 descriptions per search.'},
 {'id':'remoteok','name':'Remote OK','kind':'public-search','note':'Public JSON feed; original Remote OK links retained.'},
 {'id':'wwr','name':'We Work Remotely','kind':'public-search','note':'Public RSS feed; original listing links retained.'},
 {'id':'linkedin','name':'LinkedIn','kind':'public-search','note':'Public guest listings; no sign-in. Availability varies by region.'},
 {'id':'hiringcafe','name':'HiringCafe','kind':'public-page','note':'Reads public page data. A 403, CAPTCHA, or sign-in wall is reported, not bypassed.'},
 {'id':'remotive','name':'Remotive','kind':'public-search','note':'Remote jobs from Remotive; listings are delayed by 24 hours. Cached for six hours.'},
 {'id':'greenhouse','name':'Greenhouse','kind':'company-board','note':'Public company board API.'},
 {'id':'lever','name':'Lever','kind':'company-board','note':'Public company board API.'},
 {'id':'ashby','name':'Ashby','kind':'company-board','note':'Public company board API.'},
]
ALLOWED={'www.linkedin.com','in.linkedin.com','uk.linkedin.com','de.linkedin.com','linkedin.com','hiringcafe.com','www.hiringcafe.com','hiring.cafe','remotive.com','api.ashbyhq.com','boards-api.greenhouse.io','api.lever.co'}
ALLOWED.update({'de.linkedin.com','fr.linkedin.com','nl.linkedin.com','ie.linkedin.com','ca.linkedin.com','au.linkedin.com','sg.linkedin.com','www.arbeitnow.com','www.arbeitnow.co.uk','api.smartrecruiters.com','remoteok.com','weworkremotely.com','www.weworkremotely.com'})

class SourceUnavailable(ValueError):pass

def public_get(url,params=None):
    # Fixed public destinations only, with validation at every redirect.
    with httpx.Client(timeout=25,trust_env=False,headers={'User-Agent':'JobHunter-Local/1.0 (personal job discovery)'}) as client:
        for _ in range(4):
            try:
                parsed=urlparse(url)
                valid=parsed.scheme=='https' and parsed.hostname in ALLOWED and not parsed.username and not parsed.password and parsed.port in {None,443}
            except ValueError: valid=False
            if not valid: raise SourceUnavailable('Unsupported source URL.')
            with client.stream('GET',url,params=params) as response:
                params=None
                if response.status_code in {301,302,303,307,308}:
                    url=urljoin(url,response.headers.get('location',''));continue
                if response.status_code in {401,403,429,999}:
                    raise SourceUnavailable(f'Public access unavailable (HTTP {response.status_code}). Open the board in your browser and import a posting manually.')
                response.raise_for_status()
                content=bytearray()
                for chunk in response.iter_bytes(chunk_size=65536):
                    content.extend(chunk)
                    if len(content)>12*1024*1024:raise SourceUnavailable('Source response exceeded 12 MB.')
                return httpx.Response(response.status_code,content=bytes(content),headers={'content-type':response.headers.get('content-type','')},request=response.request)
    raise SourceUnavailable('Too many source redirects.')

def clean(value):return BeautifulSoup(html.unescape(str(value or '')),'html.parser').get_text(' ',strip=True)

def employment(value):
    return {'full_time':'Full-time','fulltime':'Full-time','full-time':'Full-time','part_time':'Part-time','parttime':'Part-time','contract':'Contract','internship':'Internship','freelance':'Freelance'}.get(str(value).lower().replace(' ',''),str(value or 'Full-time'))

def linkedin_cards(markup):
    soup=BeautifulSoup(markup,'html.parser');jobs=[]
    for card in soup.select('.base-search-card, .job-search-card'):
        title=card.select_one('.base-search-card__title');company=card.select_one('.base-search-card__subtitle');link=card.select_one('a.base-card__full-link');loc=card.select_one('.job-search-card__location')
        if not title or not link:continue
        url=link.get('href','').split('?')[0]
        if urlparse(url).hostname not in ALLOWED:continue
        jobs.append({'job_title':title.get_text(' ',strip=True),'company_name':company.get_text(' ',strip=True) if company else 'Company not listed','job_url':url,'location':loc.get_text(' ',strip=True) if loc else '', 'description':'','source':'LinkedIn','source_url':url,'posted_at':card.select_one('time').get('datetime') if card.select_one('time') else None,'requisition_id':re.search(r'(\d+)$',url).group(1) if re.search(r'(\d+)$',url) else None,'employment_type':'Full-time','description_incomplete':True})
    return list({j['job_url']:j for j in jobs}.values())

def linkedin_detail(job):
    try:
        response=public_get(job['job_url']);soup=BeautifulSoup(response.text,'html.parser')
        description=soup.select_one('.show-more-less-html__markup, .description__text')
        if description:
            job['description']=description.get_text('\n',strip=True);job['description_incomplete']=False
        else: job['detail_warning']='Description unavailable from the public page; import the full description before relying on resume ranking.'
        for item in soup.select('.description__job-criteria-item'):
            if 'employment type' in item.get_text().lower():
                value=item.select_one('.description__job-criteria-text')
                if value:job['employment_type']=employment(value.get_text(strip=True))
    except Exception:job['detail_warning']='Public job description could not be fetched. Open the original posting for details.'
    return job

def jsonld_jobs(markup,source='HiringCafe',page_url='https://hiringcafe.com/'):
    soup=BeautifulSoup(markup,'html.parser');found=[]
    def walk(node):
        if isinstance(node,list):
            for item in node:walk(item)
        elif isinstance(node,dict):
            kind=node.get('@type',[])
            if kind=='JobPosting' or isinstance(kind,list) and 'JobPosting' in kind:
                organization=node.get('hiringOrganization',{})
                location=node.get('jobLocation',[]);location=location if isinstance(location,list) else [location]
                locations=[]
                for loc in location:
                    address=loc.get('address',{}) if isinstance(loc,dict) else {}
                    if isinstance(address,str):locations.append(address)
                    else:locations.append(', '.join(str(address[k]) for k in ['addressLocality','addressRegion','addressCountry'] if address.get(k)))
                if node.get('jobLocationType')=='TELECOMMUTE':locations.append('Remote')
                url=urljoin(page_url,node.get('url',''))
                if urlparse(url).scheme!='https' or not node.get('title'):return
                found.append({'job_title':clean(node['title']),'company_name':clean(organization.get('name','Company not listed')) if isinstance(organization,dict) else clean(organization),'job_url':url,'location':' · '.join(locations),'description':clean(node.get('description','')),'employment_type':employment(node.get('employmentType','Full-time')),'source':source,'source_url':page_url,'posted_at':node.get('datePosted'),'requisition_id':node.get('identifier',{}).get('value') if isinstance(node.get('identifier'),dict) else node.get('identifier')})
            for value in node.values():
                if isinstance(value,(dict,list)):walk(value)
    for script in soup.select('script[type="application/ld+json"], script#__NEXT_DATA__'):
        try:walk(json.loads(script.string or script.get_text()))
        except (ValueError,TypeError):continue
    return list({j['job_url']:j for j in found}.values())

def retrieve(provider,board='',keywords='',location='',limit=20,page_url=''):
    if provider in {'arbeitnow','arbeitnow_uk'}:
        host='www.arbeitnow.co.uk' if provider=='arbeitnow_uk' else 'www.arbeitnow.com'
        key=provider+'-feed-v2';rows=db.query('SELECT * FROM source_cache WHERE cache_key=:key',{'key':key})
        if rows and time.time()-rows[0]['fetched_at']<21600:raw=json.loads(rows[0]['payload'])
        else:
            raw=[]
            for page in [1,2]:
                batch=public_get('https://'+host+'/api/job-board-api',params={'page':page}).json().get('data',[])
                raw.extend(batch)
                if len(batch)<100:break
            db.execute('INSERT OR REPLACE INTO source_cache VALUES (:key,:time,:payload)',{'key':key,'time':time.time(),'payload':json.dumps(raw)})
        result=[{'job_title':j['title'],'company_name':j['company_name'],'description':clean(j.get('description','')),'job_url':j['url'],'source_url':j['url'],'location':j.get('location','')+(' · Remote' if j.get('remote') else ''),'source':'Arbeitnow UK' if provider=='arbeitnow_uk' else 'Arbeitnow','posted_at':j.get('created_at'),'employment_type':'Not specified'} for j in raw]
        return [j for j in result if all(w in (j['job_title']+' '+j['description']).lower() for w in keywords.lower().split())][:limit]
    if provider=='smartrecruiters':
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',board):raise ValueError('Enter a SmartRecruiters company identifier.')
        base='https://api.smartrecruiters.com/v1/companies/'+board+'/postings'
        cards=[]
        for offset in [0,100]:
            raw=public_get(base,params={'offset':offset,'limit':100}).json();cards.extend(raw.get('content',[]))
            if raw.get('totalFound',0)<=offset+100:break
        cards=[j for j in cards if all(w in j.get('name','').lower() for w in keywords.lower().split())][:min(limit,25)]
        def detail(card):
            id=card['id']
            if not re.fullmatch(r'[A-Za-z0-9_-]+',id):raise SourceUnavailable('Invalid posting ID.')
            d=public_get(base+'/'+id).json();loc=d.get('location',{})
            return {'job_title':d['name'],'company_name':d.get('company',{}).get('name',board),'job_url':d.get('applyUrl') or 'https://jobs.smartrecruiters.com/'+board+'/'+id,'description':'\n'.join(clean(v.get('text','')) for v in d.get('jobAd',{}).get('sections',{}).values() if isinstance(v,dict)),'location':', '.join(str(loc[k]) for k in ['city','region','country'] if loc.get(k))+(' · Remote' if loc.get('remote') else ''),'employment_type':employment(d.get('typeOfEmployment',{}).get('label','Not specified')),'source':'SmartRecruiters','requisition_id':d.get('refNumber') or id,'posted_at':d.get('releasedDate') or card.get('releasedDate'),'source_url':'https://jobs.smartrecruiters.com/'+board+'/'+id}
        with ThreadPoolExecutor(max_workers=2) as pool:return list(pool.map(detail,cards))

    if provider in {'remoteok','wwr'}:
        key=provider+'-full-feed-v2'
        rows=db.query('SELECT * FROM source_cache WHERE cache_key=:key',{'key':key})
        if rows and time.time()-rows[0]['fetched_at']<21600:result=json.loads(rows[0]['payload'])
        else:
            if provider=='remoteok':
                raw=public_get('https://remoteok.com/api').json()
                result=[{'company_name':j['company'],'job_title':j['position'],'job_url':j['url'],'description':clean(j.get('description','')),'location':j.get('location','')+' · Remote','source':'Remote OK','posted_at':j.get('date') or j.get('epoch'),'requisition_id':str(j['id']) if j.get('id') else None,'source_url':j['url'],'employment_type':'Not specified'} for j in raw if j.get('position') and j.get('company') and urlparse(j.get('url','')).scheme=='https' and urlparse(j.get('url','')).hostname=='remoteok.com']
            else:
                markup=public_get('https://weworkremotely.com/remote-jobs.rss').text
                result=wwr_jobs(markup)
            db.execute('INSERT OR REPLACE INTO source_cache VALUES (:key,:time,:payload)',{'key':key,'time':time.time(),'payload':json.dumps(result)})
        words=keywords.lower().split()
        return [j for j in result if all(w in (j['job_title']+' '+j['description']).lower() for w in words)][:limit]
    if provider in {'greenhouse','lever'}:
        return [dict(j,source=provider.title(),source_url=j['job_url']) for j in fetch_feed(provider,board)][:1000]
    if provider=='ashby':
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',board):raise ValueError('Enter an Ashby company board slug.')
        response=public_get(f'https://api.ashbyhq.com/posting-api/job-board/{board}')
        return [{'company_name':board,'job_title':j['title'],'job_url':j.get('applyUrl') or j['jobUrl'],'description':j.get('descriptionPlain',''),'location':j.get('location','')+(' · Remote' if j.get('isRemote') else ''),'employment_type':employment(j.get('employmentType')),'source':'Ashby','posted_at':j.get('publishedAt'),'requisition_id':j.get('id'),'source_url':j['jobUrl']} for j in response.json().get('jobs',[]) if j.get('isListed',True)][:1000]
    if provider=='remotive':
        # Cache the complete public feed so changing a query never exceeds the advised four calls/day.
        key='remotive-full-feed-v2';rows=db.query('SELECT * FROM source_cache WHERE cache_key=:key',{'key':key})
        if rows and time.time()-rows[0]['fetched_at']<21600:raw=json.loads(rows[0]['payload'])
        else:
            raw=public_get('https://remotive.com/api/remote-jobs').json().get('jobs',[])
            db.execute('INSERT OR REPLACE INTO source_cache VALUES (:key,:time,:payload)',{'key':key,'time':time.time(),'payload':json.dumps(raw)})
        result=[{'company_name':j['company_name'],'job_title':j['title'],'job_url':j['url'],'description':clean(j.get('description','')),'location':j.get('candidate_required_location','Worldwide')+' · Remote','employment_type':employment(j.get('job_type')),'salary_text':j.get('salary',''),'source':'Remotive','posted_at':j.get('publication_date'),'requisition_id':str(j['id']) if j.get('id') else None,'source_url':j['url']} for j in raw]
        words=keywords.lower().split()
        return [j for j in result if all(w in (j['job_title']+' '+j['description']).lower() for w in words)][:limit]
    if provider=='linkedin':
        cards=linkedin_cards(public_get('https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search',params={'keywords':keywords,'location':location,'start':0}).text)[:min(limit,25)]
        if not cards:raise SourceUnavailable('No public LinkedIn cards were returned. The search may be empty or require browser access.')
        with ThreadPoolExecutor(max_workers=2) as pool:return list(pool.map(linkedin_detail,cards))
    if provider=='hiringcafe':
        url=page_url.strip() or 'https://hiringcafe.com/'
        if urlparse(url).hostname not in {'hiring.cafe','hiringcafe.com','www.hiringcafe.com'}:raise ValueError('Use a HiringCafe public page URL.')
        result=jsonld_jobs(public_get(url).text,page_url=url)
        if not result:raise SourceUnavailable('HiringCafe did not expose structured JobPosting data on this page. Open it in your browser and import the employer posting URL and description.')
        words=keywords.lower().split()
        return [j for j in result if all(w in (j['job_title']+' '+j['description']).lower() for w in words)][:limit]
    raise ValueError('Unknown job source.')

def wwr_jobs(markup):
    if '<!DOCTYPE' in markup.upper() or '<!ENTITY' in markup.upper():raise SourceUnavailable('Unsupported RSS document declarations.')
    result=[]
    for item in ET.fromstring(markup).findall('./channel/item'):
        title=item.findtext('title','');company,separator,role=title.partition(':')
        url=item.findtext('link','').strip()
        if urlparse(url).scheme!='https' or urlparse(url).hostname not in {'weworkremotely.com','www.weworkremotely.com'}:continue
        region=next((child.text or '' for child in item if child.tag.split('}')[-1]=='region'),'')
        result.append({'company_name':company.strip() if separator else 'Company not listed','job_title':role.strip() if separator else title,'job_url':url,'description':clean(item.findtext('description','')),'location':region+' · Remote','employment_type':'Not specified','source':'We Work Remotely','posted_at':item.findtext('pubDate'),'source_url':url})
    return result

def discover(provider,**kwargs):
    key=hashlib.sha256(json.dumps(['metadata-v2',provider,kwargs],sort_keys=True).encode()).hexdigest()
    rows=db.query('SELECT * FROM source_cache WHERE cache_key=:key',{'key':key})
    ttl=21600 if provider=='remotive' else 900
    if rows and time.time()-rows[0]['fetched_at']<ttl:
        result=json.loads(rows[0]['payload'])
        if result.get('error'):raise SourceUnavailable(result['error'])
        return result['jobs'],True
    try:
        jobs=retrieve(provider,**kwargs)
        if provider in {'greenhouse','lever','ashby'}:
            words=kwargs.get('keywords','').lower().split()
            jobs=[j for j in jobs if all(w in (j['job_title']+' '+j.get('description','')).lower() for w in words)][:kwargs.get('limit',20)]
        payload={'jobs':jobs}
    except Exception as exc:
        payload={'error':str(exc)[:500]}
        db.execute('INSERT OR REPLACE INTO source_cache VALUES (:key,:time,:payload)',{'key':key,'time':time.time(),'payload':json.dumps(payload)})
        raise SourceUnavailable(payload['error'])
    db.execute('INSERT OR REPLACE INTO source_cache VALUES (:key,:time,:payload)',{'key':key,'time':time.time(),'payload':json.dumps(payload)})
    return jobs,False
