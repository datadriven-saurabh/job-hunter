"""Skill frequency in a user's saved listings, with direct textual evidence."""
import re
from collections import defaultdict
from datetime import datetime, timezone
from backend.services.job_matching import SKILLS, detected, family
from backend.services.job_dedup import fingerprint


def summarize(jobs, role='', days=30, now=None):
    now = now or datetime.now(timezone.utc)
    groups = sorted({family(j.get('job_title', '')) for j in jobs if not j.get('demo')})
    sample=[]; seen=set(); unknown=0
    for job in jobs:
        if job.get('demo') or (role and family(job.get('job_title','')) != role):
            continue
        try:
            posted=datetime.fromisoformat(str(job.get('posted_at','')).replace('Z','+00:00'))
            if posted.tzinfo is None: posted=posted.replace(tzinfo=timezone.utc)
        except ValueError:
            unknown+=1
            if days: continue
            posted=None
        if posted and days and not 0 <= (now-posted).total_seconds() <= days*86400: continue
        key=fingerprint(job)
        if key in seen: continue
        seen.add(key); sample.append(job)
    evidence=defaultdict(list)
    for job in sample:
        found={}
        for line in re.split(r'\n|(?<=[.!?])\s+|;',job.get('description') or ''):
            for skill in detected(line):
                if any(re.search(r'(?<!\w)'+re.escape(alias)+r'(?!\w)\s+(?:is\s+)?not (?:required|needed|necessary)',line,re.I) for alias in SKILLS[skill]): continue
                found.setdefault(skill,line.strip())
        for skill,line in found.items():
            evidence[skill].append({'job_id':job['job_id'],'title':job['job_title'],'company':job['company_name'],'source':job.get('source','Manual import'),'posted_at':job.get('posted_at'),'quote':line[:500]})
    return {'roles':groups,'sample_size':len(sample),'unknown_dates':unknown,
            'with_description':sum(bool(j.get('description')) for j in sample),
            'skills':[{'skill':skill,'count':len(rows),'percent':round(100*len(rows)/len(sample)), 'evidence':rows}
                      for skill,rows in sorted(evidence.items(),key=lambda item:(-len(item[1]),item[0]))[:15]]}
