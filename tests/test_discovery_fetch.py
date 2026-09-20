import threading
from backend import database as db
from backend.services.discovery_fetch import fetch_sources


def test_workers_preserve_and_isolate_tenant_identity():
    for identity in ['tenant-one', 'tenant-two']:
        tokens = db.set_request_identity(identity, 'test-token')
        try:
            assert fetch_sources(['a', 'b'], lambda _: (db.current_user(), db.current_access_token())) == [(identity, 'test-token')] * 2
        finally:
            db.reset_request_identity(tokens)


def test_slow_or_failed_source_keeps_successful_results():
    release = threading.Event()
    def fetch(source):
        if source == 'slow':
            release.wait(2)
        if source == 'broken':
            raise ValueError('source unavailable')
        return source
    try:
        result = fetch_sources(['good', 'broken', 'slow'], fetch, timeout=0.1)
        assert result[0] == 'good'
        assert isinstance(result[1], ValueError)
        assert isinstance(result[2], TimeoutError)
    finally:
        release.set()
