import json
import shutil
import typst
from backend.database import DATA, ROOT, config
from backend.agents.llm import generate_json

def tailor(job, profile):
    directory = DATA / 'documents' / job['job_id']
    directory.mkdir(parents=True, exist_ok=True)
    personal, resume = profile['personal_details'], profile['base_resume']
    from backend.services import resumes
    selection=resumes.selected(job['job_id'])
    if selection and selection!='profile':
        return prepare_uploaded(job,profile,resumes.get(selection),directory)
    from backend.services.onepage import build
    from backend.services.outreach import drafts
    path=build(job,profile,directory)
    (directory/'cover-letter.txt').write_text(drafts(job,profile)['cover_letter'])
    return path,str(directory/'cover-letter.txt')


def prepare_uploaded(job,profile,selected,directory):
    """Use one resume's facts exclusively; never merge experience from variants."""
    personal=profile['personal_details']
    if selected['file_type']=='pdf':
        shutil.copy(selected['path'],directory/'resume.pdf')
    else:
        document={'name':personal['full_name'],'contact':' | '.join([personal['email'],personal['phone'],personal['location']]),'sections':[{'title':'Resume','items':[line for line in selected['text'].splitlines() if line.strip()]}]}
        (directory/'resume.json').write_text(json.dumps(document))
        shutil.copy(ROOT/'backend/templates/resume_template.typ',directory/'resume.typ')
        typst.compile(str(directory/'resume.typ'),output=str(directory/'resume.pdf'))
    keywords=[k for k in selected['keywords'] if k in job.get('description','').lower()][:6]
    letter=f"Dear {job['company_name']} hiring team,\n\nI am applying for the {job['job_title']} position. Please find my resume attached."
    if keywords:letter+=' My resume includes experience related to '+', '.join(keywords)+'.'
    letter+='\n\nI would welcome the opportunity to discuss my background and your team’s needs.\n\n'+personal['full_name']
    (directory/'cover-letter.txt').write_text(letter)
    (directory/'selection.json').write_text(json.dumps({'resume_id':selected['resume_id'],'label':selected['label']}))
    return str(directory/'resume.pdf'),str(directory/'cover-letter.txt')
