import copy
from backend.demo import PROFILE,CONFIG
from backend.services.resume_intake import profile_draft
from backend.services.resume_skills import extract_skills
from backend.services.job_matching import assess


def test_resume_skills_include_marketing_and_explicit_custom_terms():
    raw='''Taylor Sample
SUMMARY
Used SEO and Google Ads to grow acquisition. No experience in Python.
SKILLS
HubSpot, Lifecycle strategy, Braze, Email marketing
EDUCATION
Example University
'''
    result=extract_skills(raw)
    assert {'SEO','Google Ads','HubSpot','Lifecycle strategy','Braze','Email marketing'}<=set(result)
    assert 'Python' not in result and 'Example University' not in result


def test_uploaded_resume_preserves_additions_and_deduplicates():
    existing=copy.deepcopy(PROFILE)
    existing['base_resume']['structured_skills']=['Custom research','SEO']
    draft=profile_draft('Skills: SEO, HubSpot, Lifecycle strategy',existing)
    assert draft['extracted_skills']==['HubSpot','SEO','Lifecycle strategy']
    assert draft['profile']['base_resume']['structured_skills'].count('SEO')==1
    assert 'Custom research' in draft['profile']['base_resume']['structured_skills']
    assert existing['base_resume']['structured_skills']==['Custom research','SEO']


def test_custom_added_skill_contributes_only_with_literal_job_evidence():
    profile=copy.deepcopy(PROFILE)
    profile['base_resume']['structured_skills']=['Lifecycle strategy']
    fit=assess({'job_title':'Marketing Manager','location':'Remote','description':'Lifecycle strategy is required for this role.'},profile,CONFIG['job_search_criteria'])
    assert 'Lifecycle strategy' in fit['matched_skills']
    assert next(r for r in fit['requirements'] if r['skill']=='Lifecycle strategy')['profile_source']=='Listed skills'
