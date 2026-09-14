"""Private resume storage and explainable lexical matching. No cloud processing."""
import copy
from collections import Counter
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import re
import uuid
import zipfile
from xml.etree import ElementTree
from pypdf import PdfReader
from backend import database as db

MAX_BYTES=10*1024*1024
STOP=set('a an and are as at be been being by can com company contact cv date degree do edu email experience for from had has have i in including into is it its job linkedin location me my name of on or our phone present professional profile projects resume role skills summary team that the their them these they this through to university us use used using was we were will with work worked working years you your responsibilities requirements required preferred ability strong excellent knowledge'.split())
PHRASES=['machine learning','deep learning','data analysis','data engineering','data science','data analytics','business intelligence','power bi','project management','product management','system design','natural language processing','computer vision','customer service','financial analysis','stakeholder management','a/b testing','unit testing','ci/cd','supply chain','user research','cloud computing','software engineering','full stack','front end','back end']
ALIASES={'postgres':'postgresql','js':'javascript','ts':'typescript','py':'python','k8s':'kubernetes','reactjs':'react','nodejs':'node.js','golang':'go','powerbi':'power bi','scikit-learn':'sklearn'}

def keyword_counts(text):
    text=re.sub(r'https?://\S+|[\w.+-]+@[\w.-]+',' ',text.lower())
    counts=Counter()
    for token in re.findall(r'[a-z][a-z0-9]*(?:[.+#/-][a-z0-9+#]+)*',text):
        token=ALIASES.get(token,token)
        if token not in STOP and (len(token)>2 or token in {'go','r','c','c#','c++','ai','bi','ml','ux','ui'}): counts[token]+=1
    for phrase in PHRASES:
        n=len(re.findall(r'(?<!\w)'+re.escape(phrase)+r'(?!\w)',text))
        if n:counts[phrase]+=n*2
    return counts

def corpus(text):
    return [word for word,_ in keyword_counts(text).most_common(60)]

def extract_text(content, filename):
    ext=Path(filename).suffix.lower()
    if ext=='.pdf':
        if not content.startswith(b'%PDF'): raise ValueError('The file is not a valid PDF.')
        reader=PdfReader(io.BytesIO(content))
        if reader.is_encrypted: raise ValueError('Upload an unencrypted PDF.')
        if len(reader.pages)>40: raise ValueError('Resume PDFs must be 40 pages or fewer.')
        text='\n'.join(page.extract_text() or '' for page in reader.pages)
    elif ext=='.docx':
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            if sum(i.file_size for i in archive.infolist())>25*1024*1024: raise ValueError('The DOCX expands beyond the allowed size.')
            xml=archive.read('word/document.xml')
            if b'<!DOCTYPE' in xml or b'<!ENTITY' in xml: raise ValueError('Unsupported document XML.')
            root=ElementTree.fromstring(xml)
            ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            text='\n'.join(''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in root.findall('.//w:p',ns))
    elif ext=='.txt': text=content.decode('utf-8-sig')
    else: raise ValueError('Supported formats: PDF, DOCX, and UTF-8 TXT.')
    text=text.replace('\x00','').strip()
    if len(text)<40: raise ValueError('No readable resume text found. Scanned PDFs need OCR before upload; use a text-based PDF, DOCX, or TXT.')
    if len(text)>150000: raise ValueError('Resume text is too long (maximum 150,000 characters).')
    return text

def listing():
    records=db.query('SELECT resume_id,label,original_name,file_type,keywords_json,created_at,archived FROM resumes WHERE archived=0 ORDER BY created_at DESC')
    for r in records:r['keywords']=json.loads(r.pop('keywords_json'))
    profile=db.profile()
    if profile:
        base=profile_text(profile)
        records.append({'resume_id':'profile','label':'Profile resume','original_name':'From My profile','file_type':'profile','keywords':corpus(base),'created_at':None,'archived':False})
    return records

def profile_text(profile):
    r=profile['base_resume']
    return '\n'.join([r['raw_text'],' '.join(r['structured_skills'])]+[e['role']+' '+e['company']+' '+' '.join(e['bullet_points']) for e in r['experience_history']])

def get(resume_id, include_archived=False):
    if resume_id=='profile':
        p=db.profile()
        if not p:raise ValueError('Save your profile first.')
        text=profile_text(p)
        return {'resume_id':'profile','label':'Profile resume','text':text,'keywords':corpus(text),'file_type':'profile','path':None}
    rows=db.query('SELECT * FROM resumes WHERE resume_id=:id'+('' if include_archived else ' AND archived=0'),{'id':resume_id})
    if not rows:raise ValueError('Resume not found or archived.')
    r=rows[0];r['keywords']=json.loads(r.pop('keywords_json'));return r

def upload(content, filename, label):
    if not content or len(content)>MAX_BYTES: raise ValueError('Upload a nonempty resume up to 10 MB.')
    text=extract_text(content,filename)
    digest=hashlib.sha256(content).hexdigest()
    existing=db.query('SELECT resume_id FROM resumes WHERE sha256=:hash AND archived=0',{'hash':digest})
    if existing:return get(existing[0]['resume_id']),False
    resume_id=uuid.uuid4().hex
    directory=db.DATA/'resumes';directory.mkdir(parents=True,exist_ok=True)
    filename=Path(filename.replace('\\','/')).name
    path=directory/(resume_id+Path(filename).suffix.lower())
    path.write_bytes(content)
    payload={'resume_id':resume_id,'label':label.strip() or Path(filename).stem,'original_name':filename,'file_type':Path(filename).suffix.lower()[1:],'path':str(path),'text':text,'keywords_json':json.dumps(corpus(text)),'sha256':digest,'created_at':datetime.now(timezone.utc).isoformat()}
    db.execute('INSERT INTO resumes (resume_id,label,original_name,file_type,path,text,keywords_json,sha256,created_at) VALUES (:resume_id,:label,:original_name,:file_type,:path,:text,:keywords_json,:sha256,:created_at)',payload)
    return get(resume_id),True

def recommendations(job):
    candidates=[get(r['resume_id']) for r in listing()]
    jd=keyword_counts(job['job_title']+' '+job.get('description',''))
    if not candidates:return []
    vectors=[keyword_counts(r['text']) for r in candidates]
    documents=vectors+[jd];n=len(documents)
    df=Counter(k for doc in documents for k in doc)
    idf={k:1+math.log((n+1)/(v+1)) for k,v in df.items()}
    def vector(counts):return {k:(1+math.log(v))*idf[k] for k,v in counts.items()}
    target=vector(jd);target_norm=math.sqrt(sum(v*v for v in target.values()))
    output=[]
    for resume,counts in zip(candidates,vectors):
        vec=vector(counts);denom=target_norm*math.sqrt(sum(v*v for v in vec.values()))
        value=sum(v*target.get(k,0) for k,v in vec.items())/denom if denom else 0
        matched=sorted(set(counts)&set(jd),key=lambda k:-target[k])[:16]
        missing=sorted(set(jd)-set(counts),key=lambda k:-target[k])[:10]
        output.append({'resume_id':resume['resume_id'],'label':resume['label'],'score':round(value*100,1),'matched_keywords':matched,'missing_keywords':missing,'keywords':resume['keywords'],'limited_description':len(job.get('description',''))<150})
    return sorted(output,key=lambda r:(-r['score'],r['resume_id']=='profile',r['label']))

def selected(job_id):
    rows=db.query('SELECT resume_id FROM application_resume_selection WHERE job_id=:id',{'id':job_id})
    return rows[0]['resume_id'] if rows else None

def select(job_id,resume_id):
    get(resume_id)
    db.execute('INSERT INTO application_resume_selection (job_id,resume_id) VALUES (:id,:resume) ON CONFLICT(job_id) DO UPDATE SET resume_id=excluded.resume_id',{'id':job_id,'resume':resume_id})

def select_best(job):
    current=selected(job['job_id'])
    if current:
        get(current);return current
    ranked=recommendations(job)
    best=ranked[0]['resume_id'] if ranked and ranked[0]['score']>0 else 'profile'
    select(job['job_id'],best)
    return best
