"""One-page resume from exact, ranked source facts; no generative rewriting."""
import copy
from pathlib import Path
import json
import re
import shutil
import typst
from pypdf import PdfReader
from backend import database as db
from backend.services.job_matching import detected


def normalized(text):return text.replace('–','-').replace('—','-').replace('\u2011','-')


def joined_bullets(bullets):
    out=[]
    for b in bullets:
        b=b.strip()
        if not b:continue
        if out and (out[-1].endswith((',', ' and',' or')) or b[0].islower()):out[-1]+=' '+b
        else:out.append(b)
    return out


def build(job,profile,directory):
    directory.mkdir(parents=True,exist_ok=True)
    personal=profile['personal_details'];resume=profile['base_resume'];wanted=detected(job.get('description','')+' '+job['job_title'])
    def relevance(text):return len(detected(text)&wanted)*10+bool(re.search(r'\d+\s*%',text))
    skills=sorted(resume['structured_skills'],key=lambda s:-relevance(s))[:16]
    # Summary is copied from the profile, never from the reference person's resume.
    summary=resume['raw_text'].strip()
    if len(summary.split())>70:
        sentences=re.split(r'(?<=[.!?])\s+',summary)
        summary=' '.join(sentences[:2])
        if len(summary.split())>90:summary=''
    experiences=[]
    for e in sorted(resume['experience_history'],key=lambda e:e['start_date'],reverse=True)[:6]:
        bullets=sorted(joined_bullets(e['bullet_points']),key=lambda b:-relevance(b))[:3]
        experiences.append({'company':e['company'],'role':e['role'],'dates':e['start_date']+' - '+e['end_date'],'bullets':bullets})
    sections=[]
    if summary:sections.append({'title':'Summary','items':[summary]})
    if skills:sections.append({'title':'Skills','items':[' · '.join(skills)]})
    sections.append({'title':'Experience','items':experiences})
    if resume['education']:sections.append({'title':'Education','items':[f"{e['degree']}, {e['field_of_study']} - {e['institution']} ({e['graduation_year']})" for e in resume['education'][:2]]})
    doc={'name':personal['full_name'],'headline':'Target role: '+job['job_title'],'contact':' | '.join(filter(None,[personal['email'],personal['phone'],personal['location'],personal.get('linkedin_url','').replace('https://','')])),'sections':sections,'font_size':10.5}
    doc=json.loads(normalized(json.dumps(doc,ensure_ascii=False)))
    shutil.copy(db.ROOT/'backend/templates/ats_onepage.typ',directory/'resume.typ')
    removed=[]
    for attempt in range(40):
        (directory/'resume.json').write_text(json.dumps(doc,ensure_ascii=False))
        typst.compile(str(directory/'resume.typ'),output=str(directory/'resume.pdf'),font_paths=[str(p) for p in [Path('/System/Library/Fonts/Supplemental'),Path('/usr/share/fonts')] if p.exists()])
        if len(PdfReader(directory/'resume.pdf').pages)==1:
            (directory/'selection-notes.json').write_text(json.dumps({'format':'one-page ATS','source':'saved profile','omitted_bullets':removed,'note':'Ranked and selected existing facts. Full history remains in My profile. Review before sending.'}))
            return str(directory/'resume.pdf')
        # Reduce content first. Never shrink below 9.5pt or silently clip.
        entries=next(s['items'] for s in doc['sections'] if s['title']=='Experience')
        eligible=[e for e in entries if len(e['bullets'])>1]
        if eligible:
            e=min(eligible,key=lambda e:relevance(e['bullets'][-1]));removed.append(e['bullets'].pop());continue
        summary_section=next((s for s in doc['sections'] if s['title']=='Summary'),None)
        if summary_section:doc['sections'].remove(summary_section);continue
        if doc['font_size']>9.5:doc['font_size']=9.5;continue
        if len(entries)>2:
            removed.extend(entries[-1]['bullets']);entries.pop();continue
        raise ValueError('Profile content cannot fit legibly on one page. Shorten unusually long bullets or contact fields in My profile.')
    raise ValueError('Could not produce a one-page resume.')
