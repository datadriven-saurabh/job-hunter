from pathlib import Path
import re


ROOT=Path(__file__).resolve().parents[1]


def test_hosted_schema_has_rls_and_composite_tenant_keys():
    schema=(ROOT/'supabase/migrations/001_initial_schema.sql').read_text()
    rls=(ROOT/'supabase/migrations/002_rls.sql').read_text()
    assert 'primary key (user_id, job_id)' in schema
    for table in ['user_profiles','application_records','resumes','studio_kits','analysis_runs','usage_events']:
        assert f'alter table public.{table} enable row level security' in rls
    assert 'user_id = auth.uid()' in rls
    assert 'revoke all on all tables in schema public from anon, authenticated' in rls


def test_hosted_secrets_are_server_only():
    frontend='\n'.join(p.read_text(errors='ignore') for p in (ROOT/'frontend/src').rglob('*') if p.is_file())
    assert 'SUPABASE_SERVICE_ROLE_KEY' not in frontend
    assert 'DATABASE_URL' not in frontend
    assert 'OPENROUTER_API_KEY' not in frontend
    assert 'NEXT_PUBLIC_SUPABASE_ANON_KEY' in frontend
    render=(ROOT/'render.yaml').read_text()
    assert 'OPENROUTER_API_KEY' in render and 'sync: false' in render
    source='\n'.join(p.read_text(errors='ignore') for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.parts and 'node_modules' not in p.parts and '.next' not in p.parts)
    assert not re.search(r'sk-or-v1-[0-9a-f]{64}',source)
