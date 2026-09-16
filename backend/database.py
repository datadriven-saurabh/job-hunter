import json
import hashlib
import os
from pathlib import Path
from sqlalchemy import create_engine, text, event

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get('DATA_DIR', str(ROOT / 'data')))
DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
if os.name == "posix": DATA.chmod(0o700)
engine = create_engine(f'sqlite:///{DATA / "career.db"}', connect_args={'check_same_thread': False})

@event.listens_for(engine, "connect")
def enable_foreign_keys(connection, record):
    connection.execute("PRAGMA foreign_keys=ON")

def init_db():
    with engine.begin() as conn:
        conn.exec_driver_sql('PRAGMA foreign_keys=ON')
        for statement in (ROOT / 'schema.sql').read_text().split(';'):
            if statement.strip(): conn.exec_driver_sql(statement)
        conn.exec_driver_sql('CREATE TABLE IF NOT EXISTS job_details (job_id TEXT PRIMARY KEY, payload TEXT NOT NULL)')

def query(sql, params=None):
    with engine.begin() as conn:
        return [dict(row) for row in conn.execute(text(sql), params or {}).mappings()]

def execute(sql, params=None):
    with engine.begin() as conn: conn.execute(text(sql), params or {})

def profile(user_id='local'):
    rows = query('SELECT * FROM user_profiles WHERE user_id=:id', {'id': user_id})
    if not rows: return None
    r = rows[0]
    return {'user_id': r['user_id'], 'personal_details': {k: r[k] for k in ['full_name','email','phone','location','linkedin_url','github_url','portfolio_url','work_authorization']}, 'base_resume': json.loads(r['base_resume_json']), 'eeo_demographics': json.loads(r['eeo_demographics_json']) if r['eeo_demographics_json'] else None}

def config(user_id='local'):
    rows = query('SELECT * FROM system_config WHERE user_id=:id', {'id': user_id})
    if not rows: return None
    r = rows[0]
    return {k: json.loads(r[v]) for k,v in [('job_search_criteria','search_criteria_json'),('execution_preferences','execution_preferences_json'),('llm_provider_config','llm_config_json')]}

def profile_revision(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()

def applications(include_deleted=False, _job_id=None):
    where=[]
    if not include_deleted:where.append('a.job_id NOT IN (SELECT job_id FROM deleted_opportunities)')
    if _job_id is not None:where.append('a.job_id=:id')
    rows=query('SELECT a.*,d.payload,s.resume_id AS selected_resume_id,r.label AS selected_resume_label '
               'FROM application_records a LEFT JOIN job_details d ON d.job_id=a.job_id '
               'LEFT JOIN application_resume_selection s ON s.job_id=a.job_id '
               'LEFT JOIN resumes r ON r.resume_id=s.resume_id '+
               ('WHERE '+' AND '.join(where) if where else '')+' ORDER BY a.match_score DESC', {'id':_job_id})
    from backend.services.job_matching import assess
    current_profile=profile();current_config=config()
    from backend.ai.router import settings
    ai_settings=settings() if current_config else None
    for r in rows:
        r['submission_logs'] = json.loads(r.pop('submission_logs_json'))
        r['extracted_form_fields'] = json.loads(r['extracted_form_fields']) if r['extracted_form_fields'] else None
        payload=r.pop('payload')
        if payload:r.update(json.loads(payload))
        if r.get('selected_resume_id')=='profile':r['selected_resume_label']='Profile resume'
        if current_profile and current_config:
            r['fit_analysis']=assess(r,current_profile,current_config['job_search_criteria'])
            r['match_score']=r['fit_analysis']['score']/100
            from backend.services.job_intelligence import enrich, ranking
            enriched=enrich(r,r)
            for key in ['source','source_url','posted_at','posted_at_precision','first_seen_at','requisition_id','visa_status','visa_evidence','visa_source','visa_confidence','visa_conflict','visa_note','language_requirements']:r[key]=enriched[key]
            r['application_priority']=ranking(r,current_profile,r['fit_analysis']['score'],ai_settings)
    return sorted(rows,key=lambda r:r['match_score'],reverse=True)

def get_job(job_id):
    rows=applications(_job_id=job_id)
    return rows[0] if rows else None
