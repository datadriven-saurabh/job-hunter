"""Database driver types must not leak into the career-generation schema."""
import copy
import json
from uuid import UUID

import pytest
from backend import database as db
from backend.demo import PROFILE
from backend.services.career_generator import candidate


@pytest.mark.parametrize('identifier', ['local', UUID('12345678-1234-5678-1234-567812345678')])
def test_database_profile_is_valid_generation_input(monkeypatch, identifier):
    source = copy.deepcopy(PROFILE)
    row = dict(source['personal_details'], user_id=identifier,
               base_resume_json=json.dumps(source['base_resume']),
               eeo_demographics_json=json.dumps(source['eeo_demographics']) if source.get('eeo_demographics') else None)
    monkeypatch.setattr(db, 'query', lambda *args, **kwargs: [row])
    profile = db.profile()
    validated = candidate(profile)
    assert validated['user_id'] == str(identifier)
    assert json.loads(json.dumps(profile))['user_id'] == str(identifier)
    assert validated['personal_details']['full_name'] == source['personal_details']['full_name']
