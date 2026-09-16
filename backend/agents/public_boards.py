"""Bounded public-page adapters. No private APIs, sessions or guessed job facts."""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote, urlencode, urljoin, urlparse
from bs4 import BeautifulSoup

BOARDS = {
    'relocate': ('Relocate.me', 'https://relocate.me/international-jobs', r'/(?!remote/remote/the-global-move/)[^/]+/[^/]+/[^/]+/[^/]+-\d+'),
    'berlinstartupjobs': ('Berlin Startup Jobs', 'https://berlinstartupjobs.com/', r'/(?:engineering|marketing|design-ux|operations|sales|product-management|hr-recruiting|finance|internships|other)/[^/]+/'),
    'eustartups': ('EU-Startups', 'https://www.eu-startups.com/startup-jobs/', r'/job/[^/]+/'),
    'jobfluent': ('JobFluent', 'https://www.jobfluent.com/jobs-remote', r'/jobs/[^/]+'),
    'hvcapital': ('HV Capital', 'https://jobs.hvcapital.com/jobs', r'/companies/[^/]+/jobs/[^/]+'),
    'earlybird': ('Earlybird VC', 'https://jobs.earlybird.com/jobs', r'/companies/[^/]+/jobs/[^/]+'),
    'pointnine': ('Point Nine Capital', 'https://jobs.pointnine.com/jobs', r'/companies/[^/]+/jobs/[^/]+'),
    'wellfound': ('Wellfound', 'https://wellfound.com/jobs', r'/jobs/\d+[^/]*'),
    'builtin': ('Built In', 'https://builtin.com/jobs', r'/job/[^/]+/\d+'),
    'yc': ('Y Combinator', 'https://www.ycombinator.com/jobs', r'/companies/[^/]+/jobs/[^/]+'),
    'aijobs': ('AIJobs.net / Foorilla', 'https://aijobs.net/', r'/hiring/(?:job|jobs)/.+'),
    'workable': ('Workable', 'https://jobs.workable.com/', r'/view/[^/]+/.+'),
    'indeed': ('Indeed', 'https://www.indeed.com/jobs', r'/(?:viewjob|rc/clk|pagead/clk)'),
    'glassdoor': ('Glassdoor', 'https://www.glassdoor.com/Job/jobs.htm', r'/job-listing/.+'),
    'google': ('Google Jobs', 'https://www.google.com/search', r'$^'),
}
HOSTS = {urlparse(value[1]).hostname for value in BOARDS.values()} | {
    'foorilla.com', 'www.workatastartup.com', 'www.ycombinator.com',
    'hacker-news.firebaseio.com', 'news.ycombinator.com',
    'www.workingnomads.com',
}


def search_url(provider, keywords='', location=''):
    base=BOARDS[provider][1]
    slug=quote(re.sub(r'[^\w-]+','-',keywords.lower()).strip('-'),safe='-')
    if provider=='builtin' and slug:return base+'/search/'+slug
    if provider=='workable' and slug:return base+'search/global/'+slug+'-jobs'
    if provider=='indeed':return base+'?'+urlencode({'q':keywords,'l':location})
    if provider=='glassdoor':return base+'?'+urlencode({'sc.keyword':keywords})
    if provider=='google':return base+'?'+urlencode({'q':keywords+' jobs '+location})
    return base


def posting_links(markup, page_url, pattern, hosts, keywords=''):
    """Only follow observed job links on this board, including JSON-LD ItemLists."""
    soup=BeautifulSoup(markup,'html.parser');candidates=[a['href'] for a in soup.select('a[href]')]
    def walk(node):
        if isinstance(node,list):
            for item in node:walk(item)
        elif isinstance(node,dict):
            if node.get('@type')=='ListItem' and isinstance(node.get('url'),str):candidates.append(node['url'])
            for value in node.values():
                if isinstance(value,(dict,list)):walk(value)
    for script in soup.select('script[type="application/ld+json"]'):
        try:walk(json.loads(script.string or script.get_text()))
        except (ValueError,TypeError):continue
    links=[];titles={urljoin(page_url,a['href']).split('#')[0]:a.get_text(' ',strip=True) for a in soup.select('a[href]')}
    for link in candidates:
        target=urljoin(page_url,link).split('#')[0];parsed=urlparse(target)
        try:valid=parsed.scheme=='https' and parsed.hostname in hosts and not parsed.username and not parsed.password and parsed.port in {None,443}
        except ValueError:valid=False
        if valid and re.fullmatch(pattern,parsed.path) and target not in links:
            links.append(target)
    terms=keywords.casefold().split()
    return sorted(links,key=lambda link:-sum(t in (titles.get(link,'')+' '+link).casefold() for t in terms))


def jobfluent_posting(markup, page_url):
    """Read explicit JobPosting microdata, without following login links."""
    from backend.agents.job_sources import employment
    soup=BeautifulSoup(markup,'html.parser')
    root=soup.select_one('[itemtype$="/JobPosting"]')
    if not root:return []
    def value(selector):
        node=root.select_one(selector)
        return (node.get('content') or node.get_text(' ',strip=True)) if node else ''
    title=value('[itemprop="title"]');company=value('[itemprop="hiringOrganization"] [itemprop="name"]')
    if not title or not company:return []
    description=value('div[itemprop="description"]')
    remote=root.select_one('[itemprop="value"][content="TELECOMMUTE"]') is not None
    limited=root.select_one('.hide-desc-true') is not None
    return [{'job_title':title,'company_name':company,'job_url':page_url.split('?')[0],
             'description':description,'location':value('[itemprop="addressLocality"]')+(' · Remote' if remote else ''),
             'employment_type':employment(value('[itemprop="employmentType"]')),
             'posted_at':value('[itemprop="datePosted"]') or None,'source':'JobFluent','source_url':page_url,
             'description_incomplete':limited or len(description.split())<35}]


def workingnomads_jobs(keywords='',limit=20):
    from backend.agents.job_sources import public_get,clean
    from backend import database as db
    import time
    key='workingnomads-public-feed-v1';rows=db.query('SELECT * FROM source_cache WHERE cache_key=:key',{'key':key})
    if rows and time.time()-rows[0]['fetched_at']<21600:raw=json.loads(rows[0]['payload'])
    else:
        raw=public_get('https://www.workingnomads.com/api/exposed_jobs/').json()
        db.execute('INSERT OR REPLACE INTO source_cache VALUES (:key,:time,:payload)',{'key':key,'time':time.time(),'payload':json.dumps(raw)})
    jobs=[]
    for item in raw[:1000]:
        url=item.get('url','');p=urlparse(url)
        if p.scheme!='https' or p.hostname!='www.workingnomads.com' or p.username or not item.get('title') or not item.get('company_name'):continue
        description=clean(item.get('description',''))
        if not all(t in (item['title']+' '+description).casefold() for t in keywords.casefold().split()):continue
        jobs.append({'job_title':item['title'],'company_name':item['company_name'],'job_url':url,'source_url':url,
                     'description':description,'location':item.get('location','')+' · Remote','posted_at':item.get('pub_date'),
                     'source':'Working Nomads','employment_type':'Not specified','description_incomplete':len(description.split())<35})
    return jobs[:limit]


def public_page_jobs(provider, keywords='', location='', limit=20):
    from backend.agents.job_sources import public_get, jsonld_jobs, SourceUnavailable, saved_postings
    name,_,pattern=BOARDS[provider];url=search_url(provider,keywords,location)
    # AIJobs.net now redirects to Foorilla; both fixed hosts are explicitly allowed.
    hosts={urlparse(url).hostname} | ({'foorilla.com'} if provider=='aijobs' else set())
    response=public_get(url);page_url=str(response.url) if hasattr(response,'url') else url
    found=jsonld_jobs(response.text,source=name,page_url=page_url)
    if not found:
        links=posting_links(response.text,page_url,pattern,hosts,keywords)
        saved=saved_postings()
        from backend.agents.scout_agent import job_id
        # Do not refetch detail pages already saved, including deleted opportunities.
        fresh=[link for link in links if job_id(link) not in saved]
        known=[saved[job_id(link)] for link in links if job_id(link) in saved]
        def detail(link):
            try:
                markup=public_get(link).text
                result=jobfluent_posting(markup,link) if provider=='jobfluent' else jsonld_jobs(markup,source=name,page_url=link)
                return [dict(j,source_url=link) for j in result if urlparse(j['job_url']).hostname in hosts]
            except SourceUnavailable:raise
            except Exception:return []
        with ThreadPoolExecutor(max_workers=2) as pool:
            for result in pool.map(detail,fresh[:min(limit,10)]):found.extend(result)
        found.extend(known)
    if not found:
        raise SourceUnavailable(name+' returned no readable public JobPosting data. The page may require JavaScript or login, or contain no accessible listings. Open the board and import the original posting manually.')
    terms=keywords.casefold().split()
    return [dict(j,description_incomplete=j.get('description_incomplete',False) or len(j.get('description','').split())<35) for j in found if all(w in (j['job_title']+' '+j.get('description','')).casefold() for w in terms)][:limit]


def hackernews_jobs(keywords='',limit=20):
    from backend.agents.job_sources import public_get,clean,saved_postings
    from backend.agents.scout_agent import job_id
    ids=public_get('https://hacker-news.firebaseio.com/v0/jobstories.json').json()[:50]
    saved=saved_postings()
    def detail(value):
        if not isinstance(value,int):return None
        source='https://news.ycombinator.com/item?id='+str(value)
        if job_id(source) in saved:return saved[job_id(source)]
        item=public_get(f'https://hacker-news.firebaseio.com/v0/item/{value}.json').json()
        if not item or item.get('deleted') or item.get('dead') or item.get('type')!='job':return None
        title=clean(item.get('title',''));description=clean(item.get('text',''))
        company=re.split(r'\s+(?:is hiring|hiring|seeks|seeking)\b',title,flags=re.I)[0]
        if company==title:company='Company not listed'
        return {'job_title':title,'company_name':company,'job_url':source,'source_url':source,
                'employer_url':item.get('url'),'description':description,'location':'','employment_type':'Not specified',
                'posted_at':item.get('time'),'source':'Hacker News','description_incomplete':len(description.split())<35}
    with ThreadPoolExecutor(max_workers=2) as pool:rows=[j for j in pool.map(detail,ids) if j]
    return [j for j in rows if all(w in (j['job_title']+' '+j['description']).casefold() for w in keywords.casefold().split())][:limit]
