import pytest
from backend.agents.personio_feed import parse_ja_solar
from backend.agents import job_sources

XML = """<workzag-jobs><position><id>42</id><name>Business Analyst</name>
<office>Madrid</office><additionalOffices><office>Berlin</office></additionalOffices>
<createdAt>2026-01-01</createdAt><jobDescriptions><jobDescription><name>Requirements</name>
<value><![CDATA[<p>SQL and Power BI</p>]]></value></jobDescription></jobDescriptions>
</position></workzag-jobs>"""


def test_fields_and_unknown_publication_date():
    job = parse_ja_solar(XML, 'SQL')[0]
    assert job['location'] == 'Madrid, Berlin'
    assert job['description'] == 'Requirements\nSQL and Power BI'
    assert job['source_url'] == job['job_url'] == 'https://ja-solar.jobs.personio.de/job/42'
    assert job['requisition_id'] == '42' and job['description_incomplete']
    assert 'posted_at' not in job
    assert parse_ja_solar(XML, 'Python') == []
    assert parse_ja_solar(XML, limit=0) == []


@pytest.mark.parametrize('markup', ['<html>Challenge</html>', '<workzag-jobs>',
    '<!DOCTYPE x [<!ENTITY x "test">]><workzag-jobs/>'])
def test_unreadable_or_unsafe_xml_is_not_empty_success(markup):
    with pytest.raises(job_sources.SourceUnavailable):
        parse_ja_solar(markup)


def test_dedup_invalid_ids_and_bounds():
    position = XML.split('<workzag-jobs>')[1].split('</workzag-jobs>')[0]
    assert len(parse_ja_solar('<workzag-jobs>'+position*3+'</workzag-jobs>')) == 1
    assert parse_ja_solar(XML.replace('<id>42</id>', '<id>../private</id>')) == []
    assert len(parse_ja_solar('<workzag-jobs>'+''.join(position.replace('<id>42</id>',f'<id>{i}</id>') for i in range(210))+'</workzag-jobs>', limit=1000)) == 200


def test_adapter_fixed_destination(monkeypatch):
    calls = []
    class Response: text = XML
    monkeypatch.setattr(job_sources, 'public_get', lambda url: calls.append(url) or Response())
    assert len(job_sources.retrieve('ja_solar', keywords='SQL', page_url='https://private.invalid', board='ignored')) == 1
    assert calls == ['https://ja-solar.jobs.personio.de/xml?language=en']
    assert 'ja-solar.jobs.personio.de' in job_sources.ALLOWED
    assert next(s for s in job_sources.source_catalog() if s['id']=='ja_solar')['available']
