from fastapi.testclient import TestClient
from backend.main import app
from backend.services.interview_bank import bank, catalog, select_questions
from schemas import InterviewQuestion


def test_bank_integrity():
    data = bank()
    assert catalog()['total'] >= 60
    assert len({q['id'] for q in data['questions']}) == len(data['questions'])
    assert len({q['question'] for q in data['questions']}) == len(data['questions'])
    for q in select_questions():
        InterviewQuestion(**q)
        assert q['answer_guidance'] and q['follow_ups'] and q['evaluation_criteria']
        assert '{role}' not in q['question']
        assert all(s['url'].startswith('https://') and s['id'] != 'ambitionbox' for s in q['sources'])


def test_role_matching_and_no_stale_job_cache():
    job = dict(job_id='same-id', job_title='Data Analyst', company_name='Example', description='SQL dashboards')
    result = select_questions(job)
    assert result[0]['category'] == 'Behavioral'
    assert any(q['matched_topics'] == ['sql'] for q in result)
    assert not any(q['category'] == 'System Design' for q in result)
    job['job_title'] = 'Backend Software Engineer'
    assert any(q['category'] == 'System Design' for q in select_questions(job))
    job['job_title'] = 'Account Manager'
    assert not any('Software engineering' in q['role_families'] for q in select_questions(job))
    job['job_title'] = 'Nurse'
    assert all(q['role_families'] == ['General'] for q in select_questions(job))


def test_filters_and_literal_search():
    result = select_questions(role_family='Data & analytics', category='Technical', stage='Technical', query='join')
    assert result and all(q['category'] == 'Technical' for q in result)
    assert select_questions(query='no-such-question-xyz') == []
    assert select_questions(query='[') == []


def test_api_library_and_feedback(monkeypatch):
    from backend.agents import coach_agent
    monkeypatch.setattr(coach_agent, 'generate_json', lambda *a, **k: None)
    with TestClient(app) as client:
        assert client.get('/api/v1/interview/catalog').json()['total'] == 68
        result = client.get('/api/v1/interview/questions', params={'category':'Technical','query':'join'}).json()
        assert result and result[0]['answer_guidance']
        q = client.get('/api/v1/interview/questions').json()[0]
        feedback = client.post('/api/v1/interview/evaluate', json={'question_id':q['id'],'answer':'At the time my task was clear. I built a cache and reduced latency.'})
        assert feedback.status_code == 200
        assert feedback.json()['score'] == 10
        assert 'not a correctness assessment' in feedback.json()['improved_answer_suggestion']
        assert client.post('/api/v1/interview/evaluate',json={'question_id':'unknown','answer':'A long enough answer'}).status_code == 404
        assert client.get('/api/v1/interview/questions?job_id=missing').status_code == 404
        assert client.post('/api/v1/interview/evaluate',json={'job_id':'missing','question_id':q['id'],'answer':'A long enough answer'}).status_code == 404
        assert client.post('/api/v1/interview/evaluate',json={'question_id':q['id'],'answer':'short'}).status_code == 422
