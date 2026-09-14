import json
import os
from pathlib import Path
from sqlalchemy import create_engine, text, event

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get('DATA_DIR', str(ROOT / 'data')))
DATA.mkdir(parents=True, exist_ok=True)
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

def applications():
    rows = query('SELECT * FROM application_records ORDER BY match_score DESC')
    from backend.services.job_matching import assess
    current_profile=profile();current_config=config()
    for r in rows:
        r['submission_logs'] = json.loads(r.pop('submission_logs_json'))
        r['extracted_form_fields'] = json.loads(r['extracted_form_fields']) if r['extracted_form_fields'] else None
        detail = query('SELECT payload FROM job_details WHERE job_id=:id', {'id': r['job_id']})
        if detail: r.update(json.loads(detail[0]['payload']))
        selection=query('SELECT s.resume_id,r.label FROM application_resume_selection s LEFT JOIN resumes r ON r.resume_id=s.resume_id WHERE s.job_id=:id',{'id':r['job_id']})
        if selection:
            r['selected_resume_id']=selection[0]['resume_id']
            r['selected_resume_label']=selection[0]['label'] or 'Profile resume'
        if current_profile and current_config:
            r['fit_analysis']=assess(r,current_profile,current_config['job_search_criteria'])
            r['match_score']=r['fit_analysis']['score']/100
    return sorted(rows,key=lambda r:r['match_score'],reverse=True)

def get_job(job_id):
    return next((r for r in applications() if r['job_id']==job_id), None)
