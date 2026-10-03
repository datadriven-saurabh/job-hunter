import csv
import io

from fastapi.testclient import TestClient
from backend.main import app
from backend.services.opportunity_csv import cell, render

def test_csv_exports_only_selected_postings_with_full_description_and_link():
    with TestClient(app) as client:
        assert client.post('/api/v1/demo').status_code == 200
        jobs = client.get('/api/v1/applications').json()
        chosen = jobs[0]
        response = client.post('/api/v1/applications/export.csv', json={'job_ids':[chosen['job_id']]})
        assert response.status_code == 200
        assert response.headers['content-type'].startswith('text/csv')
        assert 'attachment' in response.headers['content-disposition']
        assert response.headers['cache-control'] == 'no-store'
        rows = list(csv.DictReader(io.StringIO(response.content.decode('utf-8-sig'))))
        assert len(rows) == 1
        assert rows[0]['Job Title'] == chosen['job_title']
        assert rows[0]['Job Link'] == chosen['job_url']
        assert rows[0]['Job Description'] == chosen['description']
        assert 'Fit Analysis (JSON)' in rows[0]
        assert client.post('/api/v1/applications/export.csv', json={'job_ids':['not-owned']}).status_code == 404

def test_csv_quotes_multiline_text_and_neutralizes_spreadsheet_formulas():
    body = render([{'job_title':'=HYPERLINK("https://bad.example")',
                    'company_name':'Example','job_url':'https://example.com/job',
                    'description':'First line\nSecond, quoted "line"'}])
    row = next(csv.DictReader(io.StringIO(body.lstrip('\ufeff'))))
    assert row['Job Title'].startswith("'=")
    assert row['Job Description'] == 'First line\nSecond, quoted "line"'
    assert cell(' +SUM(1,2)').startswith("' +")
