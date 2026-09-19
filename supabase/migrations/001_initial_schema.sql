-- Hosted Job Hunter schema. Apply with the Supabase SQL editor or CLI.
create extension if not exists pgcrypto;

do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'job_hunter_backend') then
    create role job_hunter_backend nologin;
  end if;
end $$;

create table if not exists public.user_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  full_name text not null default '',
  email text not null default '',
  phone text not null default '',
  location text not null default '',
  linkedin_url text default '',
  github_url text default '',
  portfolio_url text default '',
  work_authorization text not null default '',
  base_resume_json text not null default '{"raw_text":"","structured_skills":[],"experience_history":[],"education":[]}',
  eeo_demographics_json text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.system_config (
  config_id text primary key,
  user_id uuid not null unique references auth.users(id) on delete cascade,
  search_criteria_json text not null,
  execution_preferences_json text not null,
  llm_config_json text not null,
  updated_at timestamptz not null default now()
);

create table if not exists public.job_details (
  job_id text primary key,
  payload text not null
);

create table if not exists public.application_records (
  user_id uuid not null references auth.users(id) on delete cascade,
  job_id text not null,
  company_name text not null,
  job_title text not null,
  job_url text not null,
  match_score double precision not null,
  classification text not null,
  status text not null,
  tailored_resume_path text,
  tailored_cover_letter_path text,
  extracted_form_fields text,
  submission_logs_json text not null default '[]',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (user_id, job_id)
);
create index if not exists idx_apps_user_status on public.application_records(user_id, status);

create table if not exists public.resumes (
  resume_id text primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  label text not null,
  original_name text not null,
  file_type text not null,
  path text not null,
  text text not null,
  keywords_json text not null,
  sha256 text not null,
  created_at timestamptz not null default now(),
  archived boolean not null default false,
  unique (user_id, sha256)
);

create table if not exists public.application_resume_selection (
  user_id uuid not null references auth.users(id) on delete cascade,
  job_id text not null,
  resume_id text not null,
  primary key (user_id, job_id),
  foreign key (user_id, job_id) references public.application_records(user_id, job_id) on delete cascade
);

create table if not exists public.discovery_seen (
  user_id uuid not null references auth.users(id) on delete cascade,
  job_key text not null,
  content_hash text not null,
  criteria_hash text not null,
  seen_at timestamptz not null default now(),
  primary key (user_id, job_key)
);

create table if not exists public.deleted_opportunities (
  user_id uuid not null references auth.users(id) on delete cascade,
  job_id text not null,
  deleted_at timestamptz not null default now(),
  primary key (user_id, job_id),
  foreign key (user_id, job_id) references public.application_records(user_id, job_id) on delete cascade
);

create table if not exists public.studio_kits (
  kit_id text primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  job_id text,
  payload text,
  created_at timestamptz not null default now()
);
create index if not exists idx_studio_user_job on public.studio_kits(user_id, job_id, created_at desc);

create table if not exists public.studio_runs (
  user_id uuid not null references auth.users(id) on delete cascade,
  job_id text not null,
  token text not null,
  state text not null,
  error text not null default '',
  updated_at timestamptz not null default now(),
  primary key (user_id, job_id),
  foreign key (user_id, job_id) references public.application_records(user_id, job_id) on delete cascade
);

create table if not exists public.analysis_runs (
  id text primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  payload text not null,
  updated_at timestamptz not null default now()
);

create table if not exists public.usage_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  event_type text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_usage_user_day on public.usage_events(user_id, event_type, created_at desc);

create table if not exists public.source_cache (
  cache_key text primary key,
  fetched_at double precision not null,
  payload text not null
);

create or replace function public.create_job_hunter_profile()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.user_profiles(user_id, email)
  values (new.id, coalesce(new.email, ''))
  on conflict (user_id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created_job_hunter on auth.users;
create trigger on_auth_user_created_job_hunter
after insert on auth.users
for each row execute procedure public.create_job_hunter_profile();
