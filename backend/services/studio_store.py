"""Job-owned application workspaces and cancellable local generation reservations."""
import json
import re
import shutil
import uuid
from pathlib import Path
from threading import Lock
from fastapi import HTTPException
from backend import database as db
from backend.state import queue_reservation

generation_worker = Lock()

def active(job_id):
    return bool(db.query('SELECT job_id FROM application_records WHERE job_id=:id AND job_id NOT IN (SELECT job_id FROM deleted_opportunities)',{'id':job_id}))

def write_kit(path,kit):
    temporary=path/('kit-'+uuid.uuid4().hex+'.tmp')
    temporary.write_text(json.dumps(kit));temporary.replace(path/'kit.json')
    if db.HOSTED:
        from backend import storage
        prefix=f"kits/{kit['id']}"
        storage.put_user_file('artifacts',f'{prefix}/kit.json',(path/'kit.json').read_bytes(),'application/json')
        for name in ['resume.pdf','cover-letter.pdf']:
            asset=path/name
            if asset.is_file():storage.put_user_file('artifacts',f'{prefix}/{name}',asset.read_bytes(),'application/pdf')
        db.execute('UPDATE studio_kits SET payload=:payload WHERE kit_id=:id',{'payload':json.dumps(kit),'id':kit['id']})

def migrate_kits():
    """Index old on-disk kits once, preserving edits and original IDs."""
    for path in (db.DATA/'kits').glob('*/kit.json'):
        if not re.fullmatch(r'[a-f0-9]{32}',path.parent.name):continue
        try:
            kit=json.loads(path.read_text());job_id=kit.get('job',{}).get('job_id')
            if job_id and not active(job_id):
                shutil.rmtree(path.parent);continue
            if db.HOSTED:db.execute('INSERT OR IGNORE INTO studio_kits(kit_id,user_id,job_id) VALUES (:kit,:user_id,:job)',{'kit':path.parent.name,'user_id':db.current_user(),'job':job_id or None})
            else:db.execute('INSERT OR IGNORE INTO studio_kits(kit_id,job_id) VALUES (:kit,:job)',{'kit':path.parent.name,'job':job_id or None})
        except (ValueError,OSError):continue

def latest(job_id):
    rows=db.query('SELECT kit_id'+(',payload' if db.HOSTED else '')+' FROM studio_kits WHERE job_id=:id ORDER BY created_at DESC,rowid DESC',{'id':job_id})
    for row in rows:
        if db.HOSTED and row.get('payload'):return json.loads(row['payload'])
        path=db.DATA/'kits'/row['kit_id']/'kit.json'
        if path.is_file():return json.loads(path.read_text())
    return None

def kit_state(kit):
    return 'ready' if all(a.get('status')=='valid' for a in kit.get('assets',{}).values()) else 'needs_input'

def reserve(job_id,reuse=True):
    with queue_reservation:
        if not active(job_id):raise HTTPException(404,'Opportunity not found.')
        rows=db.query('SELECT * FROM studio_runs WHERE job_id=:id',{'id':job_id})
        if rows and rows[0]['state'] in {'queued','running'}:return None
        if reuse and latest(job_id):return None
        token=uuid.uuid4().hex
        if db.HOSTED:db.execute("INSERT INTO studio_runs(user_id,job_id,token,state) VALUES (:user_id,:id,:token,'queued') ON CONFLICT(user_id,job_id) DO UPDATE SET token=excluded.token,state='queued',error='',updated_at=CURRENT_TIMESTAMP",{'user_id':db.current_user(),'id':job_id,'token':token})
        else:db.execute("INSERT INTO studio_runs(job_id,token,state) VALUES (:id,:token,'queued') ON CONFLICT(job_id) DO UPDATE SET token=excluded.token,state='queued',error='',updated_at=CURRENT_TIMESTAMP",{'id':job_id,'token':token})
        return token

def current(job_id,token):
    return active(job_id) and bool(db.query('SELECT token FROM studio_runs WHERE job_id=:id AND token=:token',{'id':job_id,'token':token}))

def finish(job_id,token,state,error=''):
    if current(job_id,token):db.execute('UPDATE studio_runs SET state=:state,error=:error,updated_at=CURRENT_TIMESTAMP WHERE job_id=:id AND token=:token',{'state':state,'error':error,'id':job_id,'token':token})

def workspace(job_id):
    if not active(job_id):raise HTTPException(404,'Opportunity not found.')
    kit=latest(job_id);runs=db.query('SELECT state,error,updated_at FROM studio_runs WHERE job_id=:id',{'id':job_id})
    status=runs[0] if runs else {'state':kit_state(kit) if kit else 'not_started','error':''}
    return {**status,'kit':kit}

def remove_artifacts(job_id):
    """Caller owns queue_reservation; cancelled writers cannot publish afterwards."""
    rows=db.query('SELECT kit_id FROM studio_kits WHERE job_id=:id',{'id':job_id})
    if db.HOSTED:
        from backend import storage
        for row in rows:
            for name in ['kit.json','resume.pdf','cover-letter.pdf']:
                try:storage.delete(storage.uri('artifacts',f"{db.current_user()}/kits/{row['kit_id']}/{name}"))
                except Exception:pass
        for name in ['resume.pdf','cover-letter.txt']:
            try:storage.delete(storage.uri('artifacts',f"{db.current_user()}/documents/{job_id}/{name}"))
            except Exception:pass
        db.execute('DELETE FROM analysis_runs WHERE payload LIKE :needle',{'needle':'%"job_id": "'+job_id+'"%'})
    db.execute('DELETE FROM studio_runs WHERE job_id=:id',{'id':job_id})
    db.execute('DELETE FROM studio_kits WHERE job_id=:id',{'id':job_id})
    for row in rows:
        if re.fullmatch(r'[a-f0-9]{32}',row['kit_id']):shutil.rmtree(db.DATA/'kits'/row['kit_id'],ignore_errors=True)
    if re.fullmatch(r'[a-zA-Z0-9_-]{1,128}',job_id):shutil.rmtree(db.DATA/'documents'/job_id,ignore_errors=True)
    # Older caches were not indexed by job. Clearing derived caches leaves other
    # saved kits/profile/resume originals intact and removes cached job outputs.
    for folder in ['answer-cache','ai-cache','job-analysis-cache']:
        shutil.rmtree(db.DATA/folder,ignore_errors=True)
    for path in (db.DATA/'analysis-runs').glob('*.json'):
        try:
            result=json.loads(path.read_text())
            if job_id in result.get('job_ids',[]) or any(r.get('job_id')==job_id for r in result.get('results',[])):path.unlink(missing_ok=True)
        except (ValueError,OSError):continue
    from backend.agents.coach_agent import _sessions
    _sessions.pop((db.current_user(),job_id),None)
    db.execute('DELETE FROM application_resume_selection WHERE job_id=:id',{'id':job_id})
    db.execute("UPDATE application_records SET status='MATCHED',tailored_resume_path=NULL,tailored_cover_letter_path=NULL,extracted_form_fields=NULL,submission_logs_json='[]' WHERE job_id=:id",{'id':job_id})
