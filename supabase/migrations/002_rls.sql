-- The browser receives only the anon key. All product data goes through the
-- backend role, which gets request.jwt.claims for the verified access token.
grant usage on schema public to job_hunter_backend;
grant job_hunter_backend to postgres;
grant select, insert, update, delete on all tables in schema public to job_hunter_backend;
grant usage, select on all sequences in schema public to job_hunter_backend;

alter table public.user_profiles enable row level security;
alter table public.system_config enable row level security;
alter table public.application_records enable row level security;
alter table public.resumes enable row level security;
alter table public.application_resume_selection enable row level security;
alter table public.discovery_seen enable row level security;
alter table public.deleted_opportunities enable row level security;
alter table public.studio_kits enable row level security;
alter table public.studio_runs enable row level security;
alter table public.analysis_runs enable row level security;
alter table public.usage_events enable row level security;
alter table public.job_details enable row level security;
alter table public.source_cache enable row level security;

do $$
declare t text;
begin
  foreach t in array array[
    'user_profiles','system_config','application_records','resumes',
    'application_resume_selection','discovery_seen','deleted_opportunities',
    'studio_kits','studio_runs','analysis_runs','usage_events'
  ] loop
    execute format('drop policy if exists tenant_isolation on public.%I', t);
    execute format(
      'create policy tenant_isolation on public.%I for all to job_hunter_backend using (user_id = auth.uid()) with check (user_id = auth.uid())',
      t
    );
  end loop;
end $$;

drop policy if exists backend_shared_jobs on public.job_details;
create policy backend_shared_jobs on public.job_details for all to job_hunter_backend using (true) with check (true);
drop policy if exists backend_shared_cache on public.source_cache;
create policy backend_shared_cache on public.source_cache for all to job_hunter_backend using (true) with check (true);

-- Authenticated browser clients cannot read product tables directly. The only
-- direct browser access is Supabase Auth and the private storage policy below.
revoke all on all tables in schema public from anon, authenticated;
revoke all on all sequences in schema public from anon, authenticated;
