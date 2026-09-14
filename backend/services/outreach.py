"""Grounded drafts and explicit search leads. Never sends messages."""
import re
from urllib.parse import quote, urlparse
from backend.services.job_matching import detected
from backend.services.onepage import joined_bullets


def drafts(job,profile,recipient=''):
    wanted=detected(job['job_title']+' '+job.get('description',''))
    evidence=[(e['company'],b) for e in profile['base_resume']['experience_history'] for b in joined_bullets(e['bullet_points']) if b.strip()]
    evidence.sort(key=lambda pair:-len(detected(pair[1])&wanted))
    evidence=evidence[:2]
    name=profile['personal_details']['full_name'];company=job['company_name'];title=job['job_title']
    overlap=sorted(wanted & detected(profile['base_resume']['raw_text']+' '+' '.join(profile['base_resume']['structured_skills'])+' '+' '.join(b for _,b in evidence)))[:5]
    letter=f'Dear {company} hiring team,\n\nI am applying for the {title} position. '
    letter+=('My background includes '+', '.join(overlap)+', which are also mentioned in the posting.' if overlap else 'I would welcome the opportunity to discuss how my background relates to this role.')
    for employer,bullet in evidence:letter+='\n\nAt '+employer+': '+bullet
    letter+='\n\nI would welcome a conversation about your team’s priorities and how I could contribute. Thank you for considering my application.\n\n'+name
    greeting='Hi '+(recipient.strip().split()[0] if recipient.strip() else 'there')
    connection=f'{greeting}, I’m interested in the {title} role at {company}. I’d value connecting and learning about the team. Would you be open to discussing a referral?'
    if len(connection)>200:connection=f'{greeting}, I’m interested in a role at {company[:60]}. I’d value connecting to learn about the team and whether you’d consider a referral.'
    connection=connection[:200]
    referral=f'{greeting},\n\nI’m interested in the {title} position at {company}: {job["job_url"]}\n\n'
    if evidence:referral+='A relevant example from my work at '+evidence[0][0]+': '+evidence[0][1]+'\n\n'
    referral+='If you think my background could be a fit, would you feel comfortable referring me or pointing me toward the right person? I’m happy to share my resume. No pressure if you’re unable to help.\n\nThank you,\n'+name
    queries=[('Employees in a related team',company+' '+title),('Recruiters',company+' recruiter talent acquisition'),('Potential team leads',company+' head of analytics data manager')]
    leads=[{'label':label,'query':query,'url':'https://www.linkedin.com/search/results/people/?keywords='+quote(query),'status':'Search lead — not a verified contact'} for label,query in queries]
    contacts=[]
    flat=re.sub(r'\s+',' ',job.get('description',''))
    for match in re.finditer(r'(?:personal contact.{0,50}? is|recruiter:|hiring manager:|contact person:)\s+([A-Z][a-z]+(?: [A-Z][a-z]+){1,2})',flat):
        person=match.group(1)
        contacts.append({'name':person,'evidence':match.group(0),'source_url':job['job_url'],'url':'https://www.linkedin.com/search/results/people/?keywords='+quote(person+' '+company),'status':'Named in posting; verify current role and LinkedIn identity'})
    return {'named_contacts':contacts,'cover_letter':letter,'connection_note':connection,'referral_message':referral,'evidence':[{'company':c,'text':b} for c,b in evidence],'contact_searches':leads,'contact_note':'Search results may include former employees. Verify current employer and role; a team lead is not necessarily the hiring manager. Your connection graph is not connected to this app.'}
