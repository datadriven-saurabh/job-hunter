from datetime import datetime, timezone
from backend.services.skill_trends import summarize

NOW=datetime(2026,9,22,tzinfo=timezone.utc)
def job(id='1',**kw):
    return dict(job_id=id,job_title='Senior Data Analyst',company_name='Example',description='SQL and Python required. SQL for reporting.',posted_at='2026-09-20',**kw)

def test_counts_unique_jobs_not_mentions_and_keeps_evidence():
    result=summarize([job(),job('2')],now=NOW)
    assert result['sample_size']==1
    sql=next(s for s in result['skills'] if s['skill']=='SQL')
    assert sql['count']==1 and sql['percent']==100
    assert sql['evidence'][0]['quote']=='SQL and Python required.'

def test_filters_dates_demo_role_and_negation():
    unknown=job('2');unknown['posted_at']=None
    old=job('3');old['posted_at']='2025-01-01'
    other=job('4');other['job_title']='Frontend Developer'
    neg=job('5');neg['description']='Python is not required. Tableau preferred.'
    result=summarize([job(demo=True),unknown,old,other,neg],role='analytics',now=NOW)
    assert result['sample_size']==1 and result['unknown_dates']==1
    assert [s['skill'] for s in result['skills']]==['Tableau']
    assert summarize([unknown],days=0,now=NOW)['sample_size']==1
