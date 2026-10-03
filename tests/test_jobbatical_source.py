from types import SimpleNamespace

from backend.agents import job_sources


def test_jobbatical_search_considers_matching_titles_after_first_ten(monkeypatch):
    cards = [
        {'id': str(index), 'jobOpeningName': 'Analyst'}
        for index in range(1, 11)
    ] + [{'id': '11', 'jobOpeningName': 'Python Engineer'}]
    detail_urls = []

    def public_get(url):
        if url.endswith('/list'):
            return SimpleNamespace(json=lambda: {'result': cards})
        detail_urls.append(url)
        description = 'Python reporting' if url.endswith('/1') else 'Other work'
        return SimpleNamespace(text=f'<meta property="og:description" content="{description}">')

    monkeypatch.setattr(job_sources, 'public_get', public_get)
    jobs = job_sources.jobbatical_jobs('python', limit=20)

    assert {job['requisition_id'] for job in jobs} == {'1', '11'}
    assert len(detail_urls) == 10
