"""Synthetic cloud routing failures; never call a live model or use a real key."""
import json
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

import httpx
import pytest
from sqlalchemy import text

from backend import database as db
from backend.ai import router as module
from backend.ai.router import ModelRouter, ModelUnavailable
from backend.demo import PROFILE
from backend.prompts import build_prompt, BASE_PROMPTS
from backend.services.career_generator import Strategy

JOB = {'job_title': 'Engineer', 'company_name': 'Example', 'description': 'Python and SQL required.'}
OUTPUT = {'source_ids': ['verified'], 'priority_keywords': [], 'do_not_claim': []}


@pytest.fixture(autouse=True)
def cloud_state(monkeypatch):
    for name in ['ENABLE_GROQ', 'GROQ_FREE_TIER_CONFIRMED', 'ENABLE_OPENROUTER', 'ENABLE_LOCAL_LLM']:
        monkeypatch.setenv(name, 'false')
    monkeypatch.delenv('OPENROUTER_FREE_MODELS', raising=False)
    monkeypatch.setattr(module, '_local_budget', {})
    monkeypatch.setattr(module, '_cooldowns', {})
    monkeypatch.setattr(module, '_catalog', {'checked_at': 0, 'models': set()})
    monkeypatch.setattr(module, '_cost_guard_triggered', False)
    monkeypatch.setattr(module.httpx, 'get', lambda *a, **kw: httpx.Response(200,
        json={'data': [{'id': m, 'pricing': {'prompt': '0', 'completion': '0'}} for m in module.SAFE_FREE_MODELS]},
        request=httpx.Request('GET', module.OPENROUTER_MODELS_URL)))


def enable(monkeypatch, groq=True, openrouter=True):
    monkeypatch.setenv('ENABLE_GROQ', str(groq).lower())
    monkeypatch.setenv('GROQ_FREE_TIER_CONFIRMED', str(groq).lower())
    monkeypatch.setenv('GROQ_API_KEY', 'gsk_' + 'x' * 40)
    monkeypatch.setenv('ENABLE_OPENROUTER', str(openrouter).lower())
    monkeypatch.setenv('OPENROUTER_API_KEY', 'sk-or-v1-' + 'x' * 40)


def response(url, body, *, output=OUTPUT, status=200, cost=0, finish='stop', headers=None):
    return httpx.Response(status, request=httpx.Request('POST', url), headers=headers,
        json={'model': body.get('model') or body['models'][0],
              'choices': [{'finish_reason': finish, 'message': {'content': json.dumps(output)}}],
              'usage': {'cost': cost, 'prompt_tokens': 10, 'completion_tokens': 20}})


def prompt():
    return build_prompt('job_extraction', {}, JOB)


def test_connection_check_uses_synthetic_evidence_and_bypasses_primary(monkeypatch):
    from backend.ai.diagnostics import check_connections
    enable(monkeypatch)
    calls = []
    def post(url, **kwargs):
        body = kwargs['json']
        calls.append((url, body))
        assert 'SQL dashboards' in body['messages'][1]['content']
        assert 'personal_details' not in json.dumps(body)
        return response(url, body, output={'matched': ['SQL', 'Python'], 'missing': ['dbt']})
    monkeypatch.setattr(module.httpx, 'post', post)
    monkeypatch.setattr(db, 'profile', lambda *a: pytest.fail('Diagnostics must not load a profile'))
    result = check_connections()
    assert len(result['results']) == 4
    assert all(r['status'] == 'passed' for r in result['results'])
    assert result['fallback_check']['status'] == 'passed'
    assert result['fallback_check']['events'][0]['provider'] == 'openrouter'
    assert len(calls) == 5
    check_connections()
    assert len(calls) == 10  # Checks must call providers rather than serving cache.


def test_connection_check_rejects_bad_evidence_and_preserves_rules(monkeypatch):
    from backend.ai.diagnostics import check_connections
    enable(monkeypatch, openrouter=False)
    monkeypatch.setattr(module.httpx, 'post', lambda url, **kw: response(url, kw['json'],
        output={'matched': ['SQL', 'Python', 'Java'], 'missing': ['dbt']}))
    result = check_connections()
    assert all(r['status'] == 'failed' for r in result['results'])
    assert result['fallback_check']['status'] == 'rules_ready'
    assert result['fallback_check']['events'][-1]['provider'] == 'rules'


def test_connection_check_reports_http_status_without_credentials(monkeypatch):
    from backend.ai.diagnostics import check_connections
    enable(monkeypatch, openrouter=False)
    monkeypatch.setattr(module.httpx, 'post', lambda url, **kw: response(url, kw['json'], status=401))
    result = check_connections()
    assert result['results'][0]['events'][0]['http_status'] == 401
    assert 'gsk_' not in json.dumps(result)


def test_connection_check_is_rate_limited():
    from backend.security import _rate_event
    assert _rate_event('/api/v1/career/connection-check', 'POST')[0] == 'AI_GENERATION'


@pytest.mark.parametrize('task,model', [
    ('job_extraction', 'openai/gpt-oss-20b'), ('question_classification', 'openai/gpt-oss-20b'),
    ('outreach', 'openai/gpt-oss-20b'), ('scoring', 'openai/gpt-oss-120b'),
    ('deep_analysis', 'openai/gpt-oss-120b'), ('resume_strategy', 'openai/gpt-oss-120b'),
    ('resume_writing', 'openai/gpt-oss-120b'), ('application_answer', 'openai/gpt-oss-120b'),
])
def test_models_selected_by_task(monkeypatch, task, model):
    enable(monkeypatch)
    assert ModelRouter().get(task)['model'] == model


def test_groq_requires_explicit_free_plan_confirmation(monkeypatch):
    enable(monkeypatch)
    monkeypatch.setenv('GROQ_FREE_TIER_CONFIRMED', 'false')
    assert all(r['provider'] == 'openrouter' for r in ModelRouter()._cloud_candidates('job_extraction'))


def test_groq_redaction_strict_schema_and_cache(monkeypatch):
    enable(monkeypatch)
    calls = []
    def post(url, **kw):
        calls.append((url, kw))
        return response(url, kw['json'])
    monkeypatch.setattr(module.httpx, 'post', post)
    p = build_prompt('job_extraction', PROFILE, JOB)
    # Use a small synthetic context to fit the deliberately conservative free budget.
    p['context'] = json.dumps({'USER_PROFILE': {'personal_details': PROFILE['personal_details'],
        'base_resume': {'raw_text': 'Python. Contact taylor@example.com.'}}, 'TARGET_JOB_DESCRIPTION': JOB})
    router = ModelRouter()
    assert router.run('job_extraction', p, Strategy).source_ids == ['verified']
    assert router.run('job_extraction', p, Strategy).source_ids == ['verified']
    assert len(calls) == 1 and router.events[-1]['cache_hit']
    url, kw = calls[0]
    assert url == module.GROQ_CHAT_URL and not kw['trust_env'] and not kw['follow_redirects']
    sent = json.dumps(kw['json'])
    for private in [PROFILE['personal_details']['full_name'], PROFILE['personal_details']['email'], 'taylor@example.com']:
        assert private not in sent
    schema = kw['json']['response_format']['json_schema']['schema']
    assert set(schema['required']) == set(schema['properties'])
    assert schema['additionalProperties'] is False
    assert 'gsk_' not in (db.DATA / 'ai-usage.jsonl').read_text()


@pytest.mark.parametrize('failure', ['rate_limit', 'timeout', 'invalid_json', 'bad_evidence', 'truncated'])
def test_failures_use_openrouter_fallback(monkeypatch, failure):
    enable(monkeypatch)
    calls = []
    def post(url, **kw):
        calls.append(url)
        if url == module.GROQ_CHAT_URL:
            if failure == 'timeout':
                raise httpx.ReadTimeout('synthetic', request=httpx.Request('POST', url))
            if failure == 'invalid_json':
                return response(url, kw['json'], output='broken')
            if failure == 'bad_evidence':
                return response(url, kw['json'], output={**OUTPUT, 'source_ids': ['invented']})
            return response(url, kw['json'], status=429 if failure == 'rate_limit' else 200,
                            finish='length' if failure == 'truncated' else 'stop')
        return response(url, kw['json'])
    monkeypatch.setattr(module.httpx, 'post', post)
    def validator(result):
        if result.source_ids != ['verified']:
            raise ValueError('Unsupported evidence')
    router = ModelRouter()
    router.cache_enabled = False
    assert router.run('job_extraction', prompt(), Strategy, validator=validator).source_ids == ['verified']
    assert calls == [module.GROQ_CHAT_URL, module.OPENROUTER_CHAT_URL]
    assert router.events[-1]['fallback_used']


def test_one_retired_openrouter_model_does_not_disable_other(monkeypatch):
    enable(monkeypatch, groq=False)
    monkeypatch.setattr(module.httpx, 'get', lambda *a, **kw: httpx.Response(200,
        json={'data': [{'id': module.SAFE_FREE_MODELS[1], 'pricing': {'prompt': '0', 'completion': '0'}}]},
        request=httpx.Request('GET', module.OPENROUTER_MODELS_URL)))
    calls = []
    monkeypatch.setattr(module.httpx, 'post', lambda url, **kw: (calls.append(kw['json']) or response(url, kw['json'])))
    router = ModelRouter()
    router.cache_enabled = False
    router.run('resume_strategy', build_prompt('resume_strategy', {}, JOB), Strategy)
    assert [c['models'] for c in calls] == [[module.SAFE_FREE_MODELS[1]]]


def test_cost_guard_stops_other_cloud_routes(monkeypatch):
    enable(monkeypatch, groq=False)
    calls = []
    monkeypatch.setattr(module.httpx, 'post', lambda url, **kw: (calls.append(url) or response(url, kw['json'], cost=.1)))
    router = ModelRouter()
    router.cache_enabled = False
    with pytest.raises(ModelUnavailable):
        router.run('job_extraction', prompt(), Strategy)
    assert len(calls) == 1 and module._cost_guard_triggered


@pytest.mark.parametrize('pricing', [{}, {'prompt': '0'}, {'prompt': '0', 'completion': None}, {'prompt': '0', 'completion': '.1'}])
def test_missing_or_paid_catalog_prices_never_reach_generation(monkeypatch, pricing):
    enable(monkeypatch, groq=False)
    monkeypatch.setattr(module.httpx, 'get', lambda *a, **kw: httpx.Response(200,
        json={'data': [{'id': m, 'pricing': pricing} for m in module.SAFE_FREE_MODELS]},
        request=httpx.Request('GET', module.OPENROUTER_MODELS_URL)))
    monkeypatch.setattr(module.httpx, 'post', lambda *a, **kw: pytest.fail('Unverified price reached inference'))
    with pytest.raises(ModelUnavailable):
        ModelRouter().run('job_extraction', prompt(), Strategy)


def test_retry_budget_prevents_more_network_calls(monkeypatch):
    enable(monkeypatch)
    elapsed = [0.0]
    monkeypatch.setattr(module.time, 'monotonic', lambda: elapsed[0])
    calls = []
    def post(url, **kw):
        calls.append(url)
        elapsed[0] += 41
        raise httpx.ReadTimeout('synthetic', request=httpx.Request('POST', url))
    monkeypatch.setattr(module.httpx, 'post', post)
    with pytest.raises(ModelUnavailable):
        ModelRouter().run('job_extraction', prompt(), Strategy)
    assert len(calls) == 1


def test_all_failed_routes_end_in_rules(monkeypatch):
    enable(monkeypatch)
    calls = []
    def post(url, **kw):
        calls.append(url)
        return response(url, kw['json'], output='invalid')
    monkeypatch.setattr(module.httpx, 'post', post)
    router = ModelRouter()
    router.cache_enabled = False
    with pytest.raises(ModelUnavailable):
        router.run('job_extraction', prompt(), Strategy)
    assert len(calls) == 3 and router.events[-1]['provider'] == 'rules'


def test_large_prompt_skips_groq_without_truncating_evidence(monkeypatch):
    enable(monkeypatch)
    p = prompt()
    p['context'] = json.dumps({'USER_PROFILE': {}, 'TARGET_JOB_DESCRIPTION': {'description': 'Evidence ' * 3000}})
    calls = []
    monkeypatch.setattr(module.httpx, 'post', lambda url, **kw: (calls.append((url, kw)) or response(url, kw['json'])))
    ModelRouter().run('job_extraction', p, Strategy)
    assert len(calls) == 1 and calls[0][0] == module.OPENROUTER_CHAT_URL
    assert 'Evidence ' * 3000 in calls[0][1]['json']['messages'][1]['content']


def test_cooldown_prevents_repeated_rate_limited_calls(monkeypatch):
    enable(monkeypatch)
    calls = []
    def post(url, **kw):
        calls.append(url)
        return response(url, kw['json'], status=429 if url == module.GROQ_CHAT_URL else 200)
    monkeypatch.setattr(module.httpx, 'post', post)
    router = ModelRouter()
    router.cache_enabled = False
    router.run('job_extraction', prompt(), Strategy)
    router.run('job_extraction', prompt(), Strategy)
    assert calls.count(module.GROQ_CHAT_URL) == 1


def test_private_workflows_never_leave_backend(monkeypatch):
    enable(monkeypatch)
    monkeypatch.setattr(module.httpx, 'post', lambda *a, **kw: pytest.fail('Private data transmitted'))
    router = ModelRouter()
    with pytest.raises(ModelUnavailable):
        router.run('profile_extraction', prompt(), Strategy)
    with pytest.raises(ModelUnavailable):
        router.embed('private background')


def test_parallel_budget_is_capped_and_provider_budgets_are_separate(monkeypatch):
    monkeypatch.setenv('MAX_GROQ_REQUESTS_PER_USER_PER_DAY', '2')
    def reserve(_):
        try:
            module._consume_cloud_budget('groq', 30, 60, 120, 200, tokens=1000)
            return True
        except ModelUnavailable:
            return False
    with ThreadPoolExecutor(max_workers=8) as executor:
        assert sum(executor.map(reserve, range(12))) == 2
    module._consume_openrouter_budget()


def test_hosted_reservations_rollback_when_user_limit_is_hit(monkeypatch):
    # Run the actual conditional UPSERTs and transaction rollback on SQLite;
    # PostgreSQL uses this same SQL under its authenticated transaction wrapper.
    with db.engine.begin() as conn:
        conn.execute(text('CREATE TABLE usage_events (user_id TEXT, event_type TEXT)'))
    @contextmanager
    def transaction():
        with db.engine.begin() as conn:
            yield conn
    monkeypatch.setattr(db, 'transaction', transaction)
    monkeypatch.setattr(db, 'HOSTED', True)
    monkeypatch.setenv('MAX_GROQ_REQUESTS_PER_USER_PER_DAY', '1')
    module._consume_cloud_budget('groq', 30, 60, 120, 200, tokens=1000)
    with pytest.raises(ModelUnavailable):
        module._consume_cloud_budget('groq', 30, 60, 120, 200, tokens=1000)
    with db.engine.begin() as conn:
        rows = dict(conn.execute(text('SELECT cache_key,payload FROM source_cache')).all())
        assert sorted(rows.values()) == ['1', '1', '1000']
        assert conn.execute(text('SELECT COUNT(*) FROM usage_events')).scalar() == 1


def test_extraction_prompt_omits_architecture_document_but_writing_keeps_rules():
    assert len(prompt()['system']) < 2500
    assert 'zero fabrication' in prompt()['system']
    assert BASE_PROMPTS['resume'] in build_prompt('resume_strategy', {}, JOB)['system']
    assert BASE_PROMPTS['format'] in build_prompt('resume_writing', {}, JOB)['system']
