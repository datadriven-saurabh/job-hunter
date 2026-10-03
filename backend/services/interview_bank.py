"""Versioned, original practice prompts. No runtime scraping or model calls."""
import json
import re
from functools import lru_cache
from pathlib import Path

ROLE_TERMS = {
    'Data & analytics': ('data analyst', 'analytics', 'business intelligence', 'bi analyst'),
    'Data engineering': ('data engineer', 'etl', 'analytics engineer'),
    'Machine learning': ('machine learning', 'data scientist', 'ml engineer', 'ai engineer'),
    'Software engineering': ('software', 'frontend', 'front end', 'backend', 'back end', 'full stack', 'developer', 'devops', 'site reliability'),
    'Product & business': ('product manager', 'product owner', 'business analyst', 'project manager', 'program manager'),
    'Design': ('designer', 'ux', 'user research'),
    'Operations & commercial': ('operations', 'sales', 'account manager', 'customer success', 'marketing'),
    'Leadership': ('manager', 'director', 'head of', 'lead', 'vp'),
}

@lru_cache(maxsize=1)
def bank():
    return json.loads((Path(__file__).resolve().parents[1] / 'content/interview/questions.json').read_text())

def contains(text, term):
    return bool(re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', text.lower()))

def catalog():
    data = bank()
    return dict(version=data['version'], total=len(data['questions']), sources=data['sources'],
                categories=sorted({q['category'] for q in data['questions']}),
                role_families=['General', *ROLE_TERMS],
                stages=sorted({q['stage'] for q in data['questions']}))

def select_questions(job=None, role_family='', category='', stage='', query=''):
    title = (job or {}).get('job_title', '')
    description = (job or {}).get('description', '') or ''
    families = [role_family] if role_family else [family for family, terms in ROLE_TERMS.items() if any(contains(title, term) for term in terms)]
    sources = {s['id']: s for s in bank()['sources']}
    result = []
    for item in bank()['questions']:
        roles = item['role_families']
        if (job or role_family) and 'General' not in roles and not set(roles).intersection(families):
            continue
        if category and category != item['category'] or stage and stage != item['stage']:
            continue
        if query and query.casefold() not in ' '.join([item['question'], *item['topics'], *roles]).casefold():
            continue
        matches = [t for t in item['topics'] if contains(title + ' ' + description, t)] if job else []
        q = dict(item, sources=[sources[s] for s in item['source_ids']], matched_topics=matches)
        q['question'] = item['question'].replace('{role}', title or 'your target role').replace('{company}', (job or {}).get('company_name') or 'your target company')
        q['match_reason'] = ('Role family: ' + ', '.join(set(roles).intersection(families))) if 'General' not in roles and families else 'Broadly useful across roles'
        if matches:
            q['match_reason'] += '; job mentions ' + ', '.join(matches)
        result.append(q)
    # Start with one behavioral warmup, then prioritize evidence from the job.
    return sorted(result, key=lambda q: (q['id'] != 'q001', -len(q['matched_topics']), q['role_families'] == ['General'], q['id']))
