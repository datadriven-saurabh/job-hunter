"""Set isolation before pytest imports any application modules."""
import os
import tempfile
os.environ['DATA_DIR']=tempfile.mkdtemp(prefix='job-hunter-test-')
os.environ['ENABLE_LOCAL_LLM']='false'
os.environ['ENABLE_LIVE_SUBMISSION']='false'

import pytest
from sqlalchemy import create_engine

@pytest.fixture(autouse=True)
def isolated_database(tmp_path,monkeypatch):
    from backend import database as db
    engine=create_engine(f'sqlite:///{tmp_path / "test.db"}',connect_args={'check_same_thread':False})
    monkeypatch.setattr(db,'engine',engine)
    monkeypatch.setattr(db,'DATA',tmp_path)
    # Tailor imports this constant directly, so isolate its output directory too.
    from backend.agents import tailor_agent
    monkeypatch.setattr(tailor_agent,'DATA',tmp_path)
    db.init_db()
    yield
    engine.dispose()
