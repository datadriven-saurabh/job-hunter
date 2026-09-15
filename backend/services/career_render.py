import copy
import json
import shutil
from pathlib import Path
import typst
from pypdf import PdfReader
from backend import database as db
from backend.prompts import RESUME_FORMAT


def render_resume(asset,directory):
    if asset['status']!='valid':raise ValueError('Resolve resume validation errors before PDF export.')
    if not (db.ROOT/RESUME_FORMAT).is_file():raise ValueError('The required sanitized resume reference template is missing.')
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    doc=copy.deepcopy(asset['data']);personal=doc['personal']
    doc['contact']=' | '.join([personal['email'],personal['phone'],personal['location']])
    doc['links']=' | '.join(filter(None,[personal.get('linkedin_url'),personal.get('portfolio_url') or personal.get('github_url')]))
    for e in doc['experience']:
        def date(value):return 'Current' if value=='Present' else value[5:7]+'/'+value[:4]
        e['dates']=date(e['start_date'])+' - '+date(e['end_date'])+(' | '+e.get('location','') if e.get('location') else '')
    shutil.copy(db.ROOT/'backend/templates/career_resume.typ',directory/'resume.typ')
    for size in [10.5,10,9.5]:
        doc['font_size']=size;(directory/'resume.json').write_text(json.dumps(doc,ensure_ascii=False))
        typst.compile(str(directory/'resume.typ'),output=str(directory/'resume.pdf'),root=str(directory),font_paths=[str(p) for p in [Path('/System/Library/Fonts/Supplemental'),Path('/usr/share/fonts')] if p.exists()])
        reader=PdfReader(directory/'resume.pdf')
        if len(reader.pages)==1:
            text=reader.pages[0].extract_text()
            if personal['full_name'] not in text:raise ValueError('Resume text extraction failed.')
            (directory/'resume.md').write_text(asset['text'])
            return str(directory/'resume.pdf')
    (directory/'resume.pdf').unlink(missing_ok=True)
    raise ValueError('The validated content exceeds one page at a readable font size. Shorten source wording; content was not silently clipped or removed.')


def render_cover(asset,directory):
    if asset['status']!='valid':raise ValueError('Resolve cover-letter validation before PDF export.')
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    (directory/'cover.json').write_text(json.dumps(asset['data'],ensure_ascii=False))
    shutil.copy(db.ROOT/'backend/templates/career_cover.typ',directory/'cover.typ')
    typst.compile(str(directory/'cover.typ'),output=str(directory/'cover-letter.pdf'),root=str(directory),font_paths=[str(p) for p in [Path('/System/Library/Fonts/Supplemental'),Path('/usr/share/fonts')] if p.exists()])
    if len(PdfReader(directory/'cover-letter.pdf').pages)!=1:
        (directory/'cover-letter.pdf').unlink(missing_ok=True)
        raise ValueError('The cover letter does not fit on one page with one-inch margins.')
    return str(directory/'cover-letter.pdf')
