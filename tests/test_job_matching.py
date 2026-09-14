import copy
from fastapi.testclient import TestClient
from backend.main import app
from backend.demo import PROFILE, CONFIG
from backend.services.job_matching import assess, exclusions, experience_years


def analytics_profile():
    p=copy.deepcopy(PROFILE)
    p['base_resume'].update(raw_text='Built reporting and ETL pipelines using MySQL, Python and Power BI.',structured_skills=['Python','Power BI'],experience_history=[{'role':'Senior Analyst','company':'Example','start_date':'2020-01','end_date':'2025-01','bullet_points':['Built SQL dashboards and ETL pipelines for stakeholders using Python and Power BI.']}])
    return p


def job(title='Senior Data Analyst'):
    return {'job_title':title,'location':'Remote','employment_type':'Not specified','description':'We are looking for an analyst to build SQL dashboards using Python and Power BI. You will own ETL pipelines, partner with stakeholders, explain results and maintain reporting used by our business teams. We require 3+ years of professional experience. dbt is preferred.'}


def criteria():return dict(CONFIG['job_search_criteria'],target_roles=['Data Analyst','Analytics Engineer'],target_locations=['Remote'],required_stack_keywords=[])


def test_priority_uses_job_coverage_and_evidence():
    p=analytics_profile();fit=assess(job(),p,criteria())
    assert fit['priority']=='Apply first'
    assert 'SQL' in fit['matched_skills'] and 'dbt' in fit['missing_skills']
    sql=next(r for r in fit['requirements'] if r['skill']=='SQL')
    assert sql['profile_source']=='Senior Analyst at Example' and 'SQL dashboards' in sql['profile_evidence']
    extra=copy.deepcopy(p);extra['base_resume']['structured_skills']+=['Rust','Kubernetes','Figma']
    assert assess(job(),extra,criteria())['score']==fit['score']
    assert assess(job('Frontend Engineer'),p,criteria())['score']<50
    assert not exclusions(job(),criteria())
    assert exclusions(dict(job(),employment_type='Contract'),criteria())==['Employment type']


def test_missing_evidence_cannot_be_top_priority():
    sparse=dict(job(),description='SQL Python Power BI')
    assert assess(sparse,analytics_profile(),criteria())['priority']=='Review details'
    advanced=dict(job(),description=job()['description'].replace('3+ years','10+ years'))
    assert assess(advanced,analytics_profile(),criteria())['score']<=69
    empty=analytics_profile();empty['base_resume'].update(raw_text='',structured_skills=[],experience_history=[])
    assert assess(job(),empty,criteria())['score']<55


def test_overlapping_experience_not_double_counted():
    p=analytics_profile();p['base_resume']['experience_history']*=2
    assert experience_years(p)==5.1


def test_saved_jobs_rescore_on_profile_and_preference_change():
    with TestClient(app) as c:
        c.post('/api/v1/profile',json=analytics_profile())
        conf=copy.deepcopy(CONFIG);conf['job_search_criteria']=criteria();c.post('/api/v1/config',json=conf)
        c.post('/api/v1/jobs/import',json=dict(job(),company_name='Test',job_url='https://careers.example.com/priority'))
        before=c.get('/api/v1/applications').json()[0]
        assert before['fit_analysis']['priority']=='Apply first'
        p=analytics_profile();p['base_resume'].update(raw_text='Graphic designer working on brand illustrations.',structured_skills=['Figma'],experience_history=[])
        c.post('/api/v1/profile',json=p)
        after=c.get('/api/v1/applications').json()[0]
        assert after['match_score']<before['match_score'] and after['status']==before['status']
        conf['job_search_criteria']['target_locations']=['India'];c.post('/api/v1/config',json=conf)
        assert c.get('/api/v1/applications').json()[0]['fit_analysis']['preference_conflicts']==['Location preference']


def test_language_and_remote_restrictions_need_review():
    p=analytics_profile()
    restricted=dict(job(),description=job()['description']+' Full-remote within Germany only. You need English skills at C1 level.')
    result=assess(restricted,p,criteria())
    assert result['priority']=='Review details'
    assert any('language requirement' in w for w in result['warnings'])
    assert any('permitted work location' in w for w in result['warnings'])
    german=dict(job(),description=job()['description']+' Du sprichst gut Deutsch.')
    assert assess(german,p,criteria())['priority']=='Review details'


def test_missing_emphasized_requirement_caps_priority():
    posting=dict(job(),description=job()['description']+' Strong expertise in Databricks and dbt is required.')
    fit=assess(posting,analytics_profile(),criteria())
    assert fit['priority']!='Apply first' and fit['score']<=69
    assert next(r for r in fit['requirements'] if r['skill']=='Databricks')['importance']=='required'
