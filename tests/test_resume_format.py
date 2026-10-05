"""Resume exports match the selected layout without copying reference facts."""
import copy
import io
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from backend import database as db
from backend.demo import PROFILE
from backend.main import app
from backend.services.career_generator import generateATSResume, generateCoverLetter
from backend.services.career_render import render_resume

JOB = {'job_title': 'Software Engineer', 'company_name': 'Example',
       'description': 'Build accessible software using TypeScript, React and Python. Work with our product and design teams to deliver reliable user experiences.',
       'job_url': 'https://example.com/jobs/123'}


def assert_layout(content):
    reader = PdfReader(io.BytesIO(content))
    assert len(reader.pages) == 1
    page = reader.pages[0]
    assert tuple(float(v) for v in page.mediabox) == (0, 0, 612, 792)
    text = page.extract_text()
    assert text.index('EDUCATION') < text.index('EXPERIENCE') < text.index('ADDITIONAL')
    assert 'HAAS STUDENT' not in text and 'JP Morgan' not in text
    assert 'PROFILE' not in text and 'WORK EXPERIENCE' not in text
    assert PROFILE['personal_details']['full_name'].upper() in text
    assert PROFILE['personal_details']['email'] in text
    assert 'Software Engineer' in text and 'English' in text
    for font in page['/Resources']['/Font'].values():
        assert 'Carlito' in str(font.get_object()['/BaseFont'])
    return text


def test_letter_layout_uses_candidate_facts_and_keeps_original_asset(tmp_path):
    asset = generateATSResume(PROFILE, JOB)
    before = copy.deepcopy(asset)
    content = Path(render_resume(asset, tmp_path)).read_bytes()
    assert_layout(content)
    assert asset == before
    markdown = (tmp_path / 'resume.md').read_text()
    assert markdown.index('## EDUCATION') < markdown.index('## EXPERIENCE') < markdown.index('## ADDITIONAL')
    assert '## PROFILE' not in markdown
    for experience in asset['data']['experience']:
        for bullet in experience['bullets']:
            assert bullet['text'] in markdown


def test_oversized_role_is_not_clipped_to_one_page(tmp_path):
    asset = generateATSResume(PROFILE, JOB)
    for experience in asset['data']['experience']:
        for bullet in experience['bullets']:
            bullet['text'] *= 30
    with pytest.raises(ValueError, match='exceeds one page'):
        render_resume(asset, tmp_path)
    assert not (tmp_path / 'resume.pdf').exists()


def test_saved_studio_download_rerenders_snapshot_without_pdf_or_ai(monkeypatch):
    with TestClient(app) as client:
        assert client.post('/api/v1/profile', json=PROFILE).status_code == 200
        kit = client.post('/api/v1/studio/kits', json=JOB).json()
        assert kit['assets']['resume']['status'] == 'valid'
        path = db.DATA / 'kits' / kit['id']
        before = (path / 'kit.json').read_bytes()
        (path / 'resume.pdf').unlink()  # Old/missing hosted PDF must not determine the layout.
        from backend.ai.router import ModelRouter
        monkeypatch.setattr(ModelRouter, 'run', lambda *a, **kw: pytest.fail('A download must not call AI'))
        result = client.get(f"/api/v1/studio/kits/{kit['id']}/resume")
        assert result.status_code == 200
        assert result.headers['content-type'] == 'application/pdf'
        assert_layout(result.content)
        assert (path / 'kit.json').read_bytes() == before
        markdown = client.get(f"/api/v1/studio/kits/{kit['id']}/resume-markdown")
        assert markdown.status_code == 200 and '## ADDITIONAL' in markdown.text
        assert '## PROFILE' not in markdown.text


def test_invalid_saved_studio_resume_cannot_bypass_validation():
    with TestClient(app) as client:
        client.post('/api/v1/profile', json=PROFILE)
        kit = client.post('/api/v1/studio/kits', json=JOB).json()
        path = db.DATA / 'kits' / kit['id'] / 'kit.json'
        saved = json.loads(path.read_text())
        saved['assets']['resume']['status'] = 'needs_user_input'
        path.write_text(json.dumps(saved))
        assert client.get(f"/api/v1/studio/kits/{kit['id']}/resume").status_code == 409
        assert client.get(f"/api/v1/studio/kits/{kit['id']}/resume-markdown").status_code == 409


def test_hosted_application_pdf_upload_uses_rendered_bytes(monkeypatch):
    from backend.agents import tailor_agent
    from backend import storage
    resume, cover = generateATSResume(PROFILE, JOB), generateCoverLetter(PROFILE, JOB)
    monkeypatch.setattr(tailor_agent.resumes, 'selected', lambda *a: 'profile')
    monkeypatch.setattr(tailor_agent, 'generateATSResume', lambda *a: resume)
    monkeypatch.setattr(tailor_agent, 'generateCoverLetter', lambda *a: cover)
    monkeypatch.setattr(db, 'HOSTED', True)
    calls = []
    def put(bucket, name, content, media):
        calls.append((bucket, name, content, media))
        return 'storage://' + name
    monkeypatch.setattr(storage, 'put_user_file', put)
    result = tailor_agent.tailor({**JOB, 'job_id': 'synthetic-export'}, PROFILE)
    assert result[0].endswith('resume.pdf')
    assert_layout(calls[0][2])
