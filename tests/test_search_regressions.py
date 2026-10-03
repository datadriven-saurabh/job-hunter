"""Regression coverage for hosted LinkedIn workers and per-search locations."""
import copy
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend import database as db, main
from backend.agents import job_sources
from backend.demo import CONFIG
from backend.services.discovery_fetch import fetch_sources


def test_linkedin_detail_workers_preserve_each_tenant(monkeypatch):
    cards = ''.join(
        f'<div class="base-search-card"><a class="base-card__full-link" '
        f'href="https://www.linkedin.com/jobs/view/{i}"></a>'
        '<h3 class="base-search-card__title">Software Engineer</h3></div>'
        for i in [101, 102]
    )
    monkeypatch.setattr(job_sources, 'public_get', lambda *a, **kw: SimpleNamespace(text=cards))
    for tenant in ['tenant-a', 'tenant-b']:
        observed = []
        def query(*args, **kwargs):
            identity = (db.current_user(), db.current_access_token())
            assert identity == (tenant, tenant + '-token')
            observed.append(identity)
            return []
        monkeypatch.setattr(db, 'query', query)
        tokens = db.set_request_identity(tenant, tenant + '-token')
        try:
            result = fetch_sources(['linkedin'], lambda source: job_sources.retrieve(source))[0]
            assert isinstance(result, list), repr(result)
            assert len(result) == 2
            assert observed == [(tenant, tenant + '-token')]
        finally:
            db.reset_request_identity(tokens)


def test_linkedin_checks_multiple_public_pages_and_reports_coverage(monkeypatch):
    starts=[]
    def page(url,params=None):
        start=params['start'];starts.append(start)
        cards=''.join(
            f'<div class="base-search-card"><a class="base-card__full-link" '
            f'href="https://www.linkedin.com/jobs/view/{i}"></a>'
            '<h3 class="base-search-card__title">Software Engineer</h3></div>'
            for i in range(start+1,start+11)
        )
        return SimpleNamespace(text=cards)
    monkeypatch.setattr(job_sources,'public_get',page)
    monkeypatch.setattr(job_sources,'saved_postings',lambda:{})
    monkeypatch.setattr(job_sources,'linkedin_detail',lambda card,known:card)
    jobs=job_sources.retrieve('linkedin',limit=100)
    assert starts==[0,10,20]
    assert len(jobs)==30
    assert jobs[0]['_search_coverage']=={'cards_examined':30,'pages_scanned':3,'limited':True}


def test_linkedin_retains_first_page_if_later_page_fails(monkeypatch):
    def page(url,params=None):
        if params['start']:raise job_sources.SourceUnavailable('Public access unavailable (HTTP 429).')
        cards=''.join(
            f'<div class="base-search-card"><a class="base-card__full-link" '
            f'href="https://www.linkedin.com/jobs/view/{i}"></a>'
            '<h3 class="base-search-card__title">Software Engineer</h3></div>'
            for i in range(10)
        )
        return SimpleNamespace(text=cards)
    monkeypatch.setattr(job_sources,'public_get',page)
    monkeypatch.setattr(job_sources,'saved_postings',lambda:{})
    monkeypatch.setattr(job_sources,'linkedin_detail',lambda card,known:card)
    jobs=job_sources.retrieve('linkedin',limit=100)
    assert len(jobs)==10
    assert jobs[0]['_search_coverage']=={'cards_examined':10,'pages_scanned':1,'limited':True}


@pytest.mark.parametrize('location, expected', [('', 1), ('   ', 1), (' Tokyo ', 1), ('Berlin', 1)])
def test_search_location_overrides_saved_preferences(monkeypatch, location, expected):
    job = {'job_title': 'Software Engineer', 'company_name': 'Location Test',
           'job_url': 'https://example.com/location-test', 'location': 'Tokyo, Japan',
           'description': 'Build reliable Python software and SQL services.',
           'employment_type': 'Full-time'}
    calls = []
    def discover(provider, **kwargs):
        calls.append(kwargs['location'])
        return [dict(job)], False
    monkeypatch.setattr(main, 'discover_source', discover)
    with TestClient(main.app) as client:
        assert client.post('/api/v1/demo').status_code == 200
        config = copy.deepcopy(CONFIG)
        config['job_search_criteria']['target_locations'] = ['Berlin']
        assert client.post('/api/v1/config', json=config).status_code == 200
        result = main.execute_search(main.SearchRequest(sources=['linkedin'], location=location))
        assert result['count'] == expected, result
        assert result['sources'][0]['status'] == 'success'
        saved=next(j for j in client.get('/api/v1/applications').json() if j['company_name']=='Location Test')
        assert saved['fit_analysis']['location_conflict'] is True
        assert 'Location conflict' in saved['fit_analysis']['preference_conflicts']
        assert calls == [location.strip()]
        assert client.get('/api/v1/config').json()['job_search_criteria']['target_locations'] == ['Berlin']
