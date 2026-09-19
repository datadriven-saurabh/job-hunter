# Job Hunter — Zero-Monthly-Cost Public Deployment Instructions

## Goal

Move the existing **Job Hunter** project from a local/private setup to a small public internet deployment that:

- can be accessed by approximately **3–4 people**
- has **$0 / ₹0 recurring monthly infrastructure cost**
- supports **separate user accounts**
- keeps every user's resume, preferences, jobs, application history, generated answers, and settings isolated from other users
- keeps API keys and secrets on the server
- can be maintained primarily through GitHub
- remains simple enough to run as a personal/private beta rather than production-scale SaaS

This is intentionally an MVP deployment architecture. Do not introduce Kubernetes, AWS, paid databases, paid queues, or unnecessary infrastructure.

---

# 1. Target Architecture

Use the following architecture unless the existing repository has a strong technical reason not to.

```text
Users
  │
  ▼
Public Web App
Next.js / existing frontend
  │
  │ HTTPS
  ▼
Backend/API
existing backend or server-side API routes
  │
  ├─────────────► LLM providers / OpenRouter
  │
  ├─────────────► Job sources / search APIs
  │
  ▼
Supabase
  ├── PostgreSQL
  ├── Authentication
  └── File Storage

GitHub
  ├── source repository
  ├── CI/CD
  └── scheduled jobs if required

Hosting
  └── Vercel Hobby OR Cloudflare free tier
```

For only 3–4 users, prefer simplicity over scalability.

---

# 2. Preferred Free Stack

## Frontend

Preferred:

```text
Vercel Hobby
```

Alternative:

```text
Cloudflare Pages / Workers
```

Use Vercel when the application is primarily Next.js and deploys naturally there.

Use Cloudflare when the existing application is compatible with Workers/Pages and does not require long-running Python processes.

Do not pay for hosting for this MVP.

---

## Database

Use:

```text
Supabase PostgreSQL — Free Plan
```

As of September 2026, the Supabase Free plan includes substantially more capacity than 3–4 users should require, including a PostgreSQL database, authentication, and file storage.

Important limitation:

Free projects may be paused after prolonged inactivity.

This is acceptable for a tiny private beta.

---

## Authentication

Use:

```text
Supabase Auth
```

Initial authentication methods should be limited to:

```text
Email + password
```

Optionally add:

```text
Google OAuth
```

later.

Avoid implementing custom password authentication.

---

## File Storage

Use:

```text
Supabase Storage
```

Store user-uploaded files such as:

```text
resume.pdf
resume.docx
cover_letter.pdf
profile documents
```

Files MUST be stored inside user-specific paths.

Example:

```text
resumes/{user_id}/resume.pdf
```

Never expose the entire storage bucket publicly.

---

## Scheduled Tasks

If periodic job searches are necessary, prefer:

```text
GitHub Actions scheduled workflows
```

Example:

```yaml
schedule:
  - cron: "0 */6 * * *"
```

For only 3–4 users, running searches every few hours is preferable to keeping a worker running continuously.

Alternative:

```text
Cloudflare Cron Triggers
```

Do not introduce Redis/Celery unless the current architecture already requires them.

---

# 3. Strict Cost Requirement

The target recurring infrastructure cost is:

```text
₹0/month
```

The following MAY still cost money and therefore must be treated separately:

1. Custom domain
2. Paid LLM/API usage
3. Paid job-search APIs
4. CAPTCHA-solving services
5. Browser automation infrastructure
6. Premium email services

The application must work without purchasing a custom domain.

Example free deployment URL:

```text
https://job-hunter.vercel.app
```

or an equivalent provider-generated URL.

---

# 4. Multi-User Architecture

The existing project may currently assume one global user.

Refactor all user-specific data to belong to an authenticated user.

Every persisted user-owned object MUST contain:

```text
user_id
```

where appropriate.

Recommended schema:

```text
profiles
resumes
user_preferences
job_searches
jobs
job_matches
applications
application_questions
generated_answers
saved_jobs
user_integrations
usage_events
```

---

# 5. Core Database Schema

## profiles

```sql
create table profiles (
    id uuid primary key references auth.users(id) on delete cascade,
    full_name text,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);
```

---

## resumes

```sql
create table resumes (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    name text not null,
    storage_path text,
    parsed_content jsonb,
    is_primary boolean default false,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);
```

---

## user_preferences

```sql
create table user_preferences (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null unique references auth.users(id) on delete cascade,

    target_roles text[],
    target_locations text[],
    excluded_locations text[],
    visa_sponsorship_required boolean default false,
    remote_preference text,

    minimum_salary numeric,
    preferred_languages text[],

    preferences jsonb default '{}'::jsonb,

    created_at timestamptz default now(),
    updated_at timestamptz default now()
);
```

---

## jobs

Jobs themselves can be shared globally.

```sql
create table jobs (
    id uuid primary key default gen_random_uuid(),
    source text,
    external_id text,
    company text,
    title text,
    location text,
    description text,
    apply_url text,
    metadata jsonb,
    first_seen_at timestamptz default now(),
    last_seen_at timestamptz default now(),

    unique(source, external_id)
);
```

Do NOT duplicate the same public job separately for every user.

---

## job_matches

Store user-specific ranking separately.

```sql
create table job_matches (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    job_id uuid not null references jobs(id) on delete cascade,

    score numeric,
    reasoning jsonb,
    status text default 'new',

    created_at timestamptz default now(),

    unique(user_id, job_id)
);
```

---

## applications

```sql
create table applications (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    job_id uuid references jobs(id) on delete set null,

    status text default 'saved',
    applied_at timestamptz,
    notes text,

    created_at timestamptz default now(),
    updated_at timestamptz default now()
);
```

Suggested statuses:

```text
saved
preparing
applied
assessment
interview
offer
rejected
withdrawn
```

---

## generated_answers

```sql
create table generated_answers (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    job_id uuid references jobs(id) on delete cascade,

    question text not null,
    answer text not null,

    model_used text,
    metadata jsonb,

    created_at timestamptz default now()
);
```

---

# 6. Row Level Security — Mandatory

Authentication alone is NOT sufficient.

Enable Supabase Row Level Security on every table containing user-owned data.

Example:

```sql
alter table resumes enable row level security;
```

Add policies such as:

```sql
create policy "Users can read own resumes"
on resumes
for select
using (auth.uid() = user_id);
```

```sql
create policy "Users can create own resumes"
on resumes
for insert
with check (auth.uid() = user_id);
```

```sql
create policy "Users can update own resumes"
on resumes
for update
using (auth.uid() = user_id);
```

```sql
create policy "Users can delete own resumes"
on resumes
for delete
using (auth.uid() = user_id);
```

Equivalent policies must exist for all user-specific tables.

At minimum:

```text
profiles
resumes
user_preferences
job_matches
applications
generated_answers
saved_jobs
user_integrations
```

Never rely only on frontend filtering such as:

```javascript
.filter(row => row.user_id === user.id)
```

Database-level isolation is mandatory.

---

# 7. Authentication Flow

Implement the following pages/routes:

```text
/login
/signup
/logout
/dashboard
```

Unauthenticated users trying to access private routes must be redirected to:

```text
/login
```

Expected flow:

```text
User opens website
        ↓
Supabase session check
        ↓
No session ─────► Login
        │
        ▼
Authenticated
        │
        ▼
Dashboard
```

After successful registration:

1. Supabase creates `auth.users` entry.
2. Create corresponding `profiles` row.
3. Redirect user to onboarding.
4. Ask user to upload their resume.
5. Ask for job-search preferences.
6. Save all preferences against authenticated `user_id`.

---

# 8. User Onboarding

Each new user should complete:

```text
1. Create account
2. Upload resume
3. Parse resume
4. Confirm profile
5. Select target job titles
6. Select target countries/locations
7. Set relocation preference
8. Set visa sponsorship requirement
9. Set remote/hybrid/on-site preference
10. Save profile
```

Do not hard-code the original owner's resume or preferences.

---

# 9. Remove Global Personal Context

Search the codebase for hard-coded assumptions such as:

```text
MY_RESUME
resume.json
profile.json
preferences.json
candidate_context.md
USER_PROFILE
Saurabh
Tushar
specific email address
specific target countries
```

Replace them with database-backed user-specific data.

Bad:

```python
resume = load_file("resume.md")
```

Good:

```python
resume = get_primary_resume(user_id)
```

Bad:

```python
preferences = DEFAULT_JOB_PREFERENCES
```

Good:

```python
preferences = get_user_preferences(user_id)
```

---

# 10. Authentication Must Reach the Backend

Never trust a `user_id` supplied directly by the frontend.

BAD:

```http
POST /api/generate-answer

{
  "user_id": "123",
  "question": "Why should we hire you?"
}
```

Instead:

```http
Authorization: Bearer <supabase_access_token>
```

The backend must:

1. validate the Supabase token
2. determine the authenticated user ID
3. ignore any client-provided user identity
4. query only records belonging to that user

Pseudo-flow:

```python
user = verify_access_token(request)

user_id = user.id

resume = db.get_primary_resume(user_id)
preferences = db.get_preferences(user_id)
```

---

# 11. API Security

Every private endpoint must require authentication.

Examples:

```text
/api/profile
/api/resume
/api/jobs
/api/matches
/api/generate-answer
/api/applications
/api/search-jobs
```

Public endpoints should be minimal.

Potential public routes:

```text
/
/health
/login
/signup
```

Do not expose internal debug routes.

---

# 12. Secrets

Create:

```text
.env.example
```

with variable NAMES only.

Example:

```bash
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

OPENROUTER_API_KEY=
OPENAI_API_KEY=

APP_URL=
ENVIRONMENT=
```

Never commit real secrets.

Ensure `.gitignore` contains:

```text
.env
.env.local
.env.production
*.pem
credentials.json
secrets.json
```

---

# 13. Service Role Key Rules

`SUPABASE_SERVICE_ROLE_KEY` must NEVER be sent to the browser.

It may only exist:

```text
backend environment variables
server-side functions
trusted scheduled workers
```

Frontend may use:

```text
SUPABASE_URL
SUPABASE_ANON_KEY
```

with Row Level Security enabled.

---

# 14. LLM API Keys

Do NOT put:

```text
OPENAI_API_KEY
OPENROUTER_API_KEY
ANTHROPIC_API_KEY
GEMINI_API_KEY
```

inside frontend JavaScript.

All LLM requests must go:

```text
Browser
  ↓
Your backend
  ↓
LLM provider
```

Never:

```text
Browser
  ↓
LLM provider directly using private server key
```

---

# 15. Prevent One User From Consuming Everything

Even with only 3–4 people, implement basic limits.

Recommended MVP limits:

```text
job searches:            10/day/user
AI-generated answers:    30/day/user
resume parses:            5/day/user
manual refreshes:        10/day/user
```

Store counters in the database if convenient.

Do not build complex billing.

Simple server-side rate limiting is sufficient.

---

# 16. AI Cost Protection

Infrastructure can remain free while LLM usage generates charges.

Therefore build a model router.

Suggested hierarchy:

```text
Tier 0
No LLM

Tier 1
Free / extremely cheap model

Tier 2
Mid-tier model

Tier 3
Flagship model
```

---

## Tier 0 — No LLM

Use deterministic code for:

```text
deduplication
exact keyword matching
URL normalization
date parsing
company normalization
basic filters
database operations
```

---

## Tier 1 — Cheap/Free Model

Use for:

```text
job classification
basic structured extraction
simple summarization
yes/no relevance filtering
skill extraction
```

---

## Tier 2 — Mid-Tier Model

Use for:

```text
resume ↔ JD analysis
job-fit reasoning
application question drafts
resume bullet adaptation
```

---

## Tier 3 — Flagship Model

Use only for:

```text
complex application questions
final answer polishing
high-value resume tailoring
difficult reasoning
```

The strongest model must NOT be the default model.

---

# 17. Cache AI Results

Before calling an LLM, check whether an equivalent result already exists.

Example:

```text
same user
+
same resume version
+
same job
+
same question
```

Then reuse the existing generated answer where appropriate.

Potential cache key:

```text
SHA256(
  user_id +
  resume_version +
  job_id +
  normalized_question +
  prompt_version
)
```

This reduces token usage significantly.

---

# 18. Resume Parsing

Parse a resume once when uploaded.

Store a structured representation.

Example:

```json
{
  "summary": "...",
  "skills": [],
  "experience": [],
  "education": [],
  "projects": [],
  "achievements": []
}
```

Do not repeatedly send the entire raw PDF to the model.

Store:

```text
raw file
+
parsed structured profile
+
optional compact AI context
```

---

# 19. Per-User AI Context

Build application prompts dynamically.

Concept:

```text
system instructions
+
relevant resume sections
+
relevant user experience snippets
+
job description
+
question
```

Do NOT send:

```text
every previous conversation
every generated answer
entire application history
all stored jobs
```

Use retrieval based on relevance.

---

# 20. Job Discovery Design

For 3–4 users, do not run separate crawling infrastructure for every person.

Preferred pipeline:

```text
Scheduled fetch
       ↓
collect jobs
       ↓
normalize
       ↓
deduplicate
       ↓
store once in jobs table
       ↓
score relevant jobs per user
       ↓
job_matches
```

Shared job storage dramatically reduces duplicate work.

---

# 21. Scheduled Job Search

For the MVP, use a GitHub Actions cron.

Example workflow:

```yaml
name: Refresh Jobs

on:
  schedule:
    - cron: "0 */6 * * *"

  workflow_dispatch:

jobs:
  refresh:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - run: pip install -r requirements.txt

      - run: python scripts/refresh_jobs.py
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
          OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
```

Adjust language/runtime to the repository.

Do not run refresh jobs every few minutes.

For 3–4 people:

```text
every 4–6 hours
```

is enough initially.

---

# 22. Browser Automation

If Job Hunter currently controls Chrome/Playwright/Selenium:

Do NOT immediately deploy browser automation to serverless hosting.

Vercel/Cloudflare are not the ideal place for long-running browser sessions.

For the first public version:

```text
Phase 1:
job discovery
job matching
resume tailoring
application question generation
application tracking
```

Keep fully automated browser-based job submission optional.

If browser automation is essential, evaluate it separately.

The $0/month requirement takes priority over autonomous application submission.

---

# 23. Deployment Strategy

## Step 1 — Put project in GitHub

Ensure repository contains:

```text
README.md
.env.example
.gitignore
requirements.txt / package.json
database migrations
deployment configuration
```

Remove secrets from Git history if any were previously committed.

Rotate leaked keys.

---

## Step 2 — Create Supabase project

Create one free Supabase project.

Configure:

```text
Postgres
Auth
Storage
RLS
```

Create all migrations in source control.

Recommended structure:

```text
supabase/
  migrations/
    001_initial_schema.sql
    002_rls.sql
    003_storage.sql
```

Database schema must be reproducible from the repository.

---

## Step 3 — Implement auth

Create:

```text
signup
login
logout
session handling
protected routes
```

Test using at least two accounts.

---

## Step 4 — Implement per-user database access

Replace global profile/resume state with authenticated user state.

Every endpoint must be audited.

---

## Step 5 — Deploy frontend/backend

If compatible with Vercel:

```text
GitHub repo
     ↓
Vercel project
     ↓
automatic deploy on main branch
```

Set environment variables through the hosting provider.

Do not commit production `.env`.

---

## Step 6 — Configure production URLs

Set:

```text
APP_URL=<public deployment URL>
```

Configure Supabase Auth redirect URLs accordingly.

For example:

```text
https://your-project.vercel.app/**
```

Do not leave authentication callbacks limited to localhost.

---

# 24. Recommended Branch Workflow

Use:

```text
main
develop
feature/*
```

Example:

```text
feature/auth
feature/multi-user-db
feature/deployment
```

Deploy production from:

```text
main
```

For a tiny project, do not over-engineer Git workflows.

---

# 25. Minimum Security Checklist

Before sharing the URL:

- [ ] No API keys exist in frontend code
- [ ] No secrets exist in Git history
- [ ] Authentication required for dashboard
- [ ] RLS enabled
- [ ] User A cannot read User B's resume
- [ ] User A cannot read User B's generated answers
- [ ] User A cannot modify User B's applications
- [ ] Storage files are private
- [ ] Backend validates access tokens
- [ ] Service role key remains server-side
- [ ] Debug routes disabled
- [ ] Error messages do not expose secrets
- [ ] LLM usage has rate limits
- [ ] Job refresh has bounded frequency

---

# 26. Critical Multi-User Test

Create:

```text
test-user-a@example.com
test-user-b@example.com
```

Upload different resumes.

Verify:

```text
A login → sees only A data
B login → sees only B data
```

Then attempt manually:

```text
A requesting B resume ID
A requesting B application ID
A requesting B generated-answer ID
```

Expected result:

```text
404 / 403 / empty result
```

Never rely solely on UI testing.

---

# 27. Storage Security

Use bucket:

```text
resumes
```

Path:

```text
{auth.uid()}/{uuid}.pdf
```

Storage policy concept:

```text
Users may only access objects whose first directory equals auth.uid()
```

Do not generate permanent public URLs for resumes.

Use:

```text
authenticated download
```

or:

```text
short-lived signed URL
```

where required.

---

# 28. Logging

Log:

```text
timestamp
request ID
user ID
action
success/failure
provider
latency
token usage
```

Never log:

```text
password
full access token
API key
service role key
full sensitive resume text unless required
```

---

# 29. Usage Tracking

A lightweight table is sufficient.

```sql
create table usage_events (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references auth.users(id) on delete cascade,
    event_type text not null,
    metadata jsonb default '{}'::jsonb,
    created_at timestamptz default now()
);
```

Possible events:

```text
JOB_SEARCH
JOB_MATCH
RESUME_PARSE
ANSWER_GENERATION
APPLICATION_CREATED
LOGIN
```

Use this to diagnose excessive usage before adding billing.

---

# 30. Backups

Supabase Free does not provide the same backup guarantees as paid production tiers.

For a 3–4-person MVP, create a simple periodic logical backup if desired.

For example:

```text
weekly export
```

Store backup securely.

Do not commit database dumps containing personal information to a public GitHub repository.

---

# 31. Public vs Private GitHub Repository

Prefer:

```text
private repository
```

because Job Hunter may contain:

```text
prompts
automation logic
integration code
personal workflow assumptions
```

A public deployment does NOT require a public GitHub repository.

---

# 32. Deployment URL

Initially use the hosting provider's free URL.

Example:

```text
https://job-hunter-xyz.vercel.app
```

Do not purchase a domain until the product is worth keeping.

---

# 33. Keep the App Private-ish Despite Being Internet Accessible

Because only 3–4 users need access, optionally disable open registration.

Preferred private-beta option:

```text
ALLOW_SIGNUPS=false
```

Create approved users manually or maintain an allowlist.

Example:

```text
allowed_users
```

Schema:

```sql
create table allowed_users (
    email text primary key,
    created_at timestamptz default now()
);
```

On signup:

```text
if email not in allowlist:
    reject registration
```

This prevents random internet visitors from consuming your API quotas.

Alternative:

Keep signup enabled but require an invite code.

For only 3–4 users, an allowlist is simpler.

---

# 34. Recommended MVP User Model

Use:

```text
ADMIN
USER
```

No complex permissions are required.

Admin can:

```text
view system health
trigger job refresh
manage approved users
inspect aggregate usage
```

Admin should NOT casually browse private user resume/application content unless explicitly necessary.

---

# 35. Free-Tier Protection

Implement hard limits so a bug cannot create runaway usage.

Examples:

```text
MAX_JOBS_PER_REFRESH=500
MAX_AI_CALLS_PER_USER_PER_DAY=30
MAX_SEARCHES_PER_USER_PER_DAY=10
MAX_RESUME_SIZE_MB=5
MAX_ACTIVE_RESUMES_PER_USER=3
```

Set API request timeouts.

Set LLM maximum tokens.

Set crawler page limits.

---

# 36. Recommended Deployment Order for the Coding Agent

Implement in this exact order:

```text
1. Audit current repository
2. Identify frontend/backend architecture
3. Identify all global/local user state
4. Introduce Supabase
5. Create database migrations
6. Add authentication
7. Add RLS
8. Refactor resume storage per user
9. Refactor preferences per user
10. Refactor job matches per user
11. Refactor applications per user
12. Refactor generated answers per user
13. Protect backend endpoints
14. Move all secrets server-side
15. Add usage limits
16. Add GitHub scheduled refresh
17. Add deployment config
18. Deploy
19. Run two-user isolation tests
20. Share beta URL
```

Do NOT change core job-matching behavior until multi-user isolation works.

---

# 37. Coding-Agent Rules

When implementing this migration:

1. Inspect the repository before selecting frameworks.
2. Reuse the existing frontend/backend wherever practical.
3. Avoid unnecessary rewrites.
4. Prefer migration in small commits.
5. Preserve current Job Hunter behavior.
6. Do not remove existing features without a documented reason.
7. Do not introduce paid dependencies.
8. Prefer provider free tiers.
9. Never expose secrets to the client.
10. Never trust a frontend-provided `user_id`.
11. Apply RLS to all user-owned tables.
12. Keep jobs globally reusable where possible.
13. Keep matches/applications private per user.
14. Keep AI model choice configurable.
15. Provide `.env.example`.
16. Add setup instructions to `README.md`.
17. Add database migration instructions.
18. Add deployment instructions.
19. Add rollback instructions.
20. Add tests for multi-user isolation.

---

# 38. Definition of Done

The project is ready when all of the following are true.

## Internet access

```text
A public HTTPS URL exists.
```

---

## Authentication

```text
User can:
- sign up or accept invite
- log in
- log out
- maintain session
```

---

## User isolation

Each user has independent:

```text
resume
profile
preferences
job matches
saved jobs
applications
generated answers
```

---

## Shared resources

Common public jobs may be stored once.

---

## Security

```text
No secret is exposed.
RLS is enabled.
Backend validates identity.
```

---

## Cost

Recurring infrastructure:

```text
₹0/month
```

excluding optional external API/LLM consumption and domain registration.

---

## Availability

3–4 invited users can use the application independently through the public URL.

---

# 39. Recommended Final MVP Stack

Unless repository constraints require otherwise, target:

```text
Repository       → GitHub
Frontend         → Next.js / existing frontend
Hosting          → Vercel Hobby
Database         → Supabase PostgreSQL Free
Authentication   → Supabase Auth
File Storage     → Supabase Storage
Scheduled Jobs   → GitHub Actions
AI               → existing model router/OpenRouter
Monitoring       → provider logs
Domain           → free *.vercel.app URL
```

Expected recurring infrastructure cost:

```text
₹0/month
```

for a very small private beta.

---

# 40. Important Non-Goals

Do NOT implement these during this migration unless already required:

```text
Kubernetes
AWS ECS
AWS RDS
paid Redis
Kafka
microservices
complex queues
multi-region architecture
billing/subscriptions
enterprise RBAC
paid domain
paid monitoring
24/7 dedicated worker
```

The goal is not to build a large SaaS platform.

The goal is:

```text
Make the existing Job Hunter safely accessible
to 3–4 independent users over the internet
with no recurring infrastructure bill.
```

---

# 41. Final Instruction to the Coding Agent

Begin by auditing the current repository.

Before editing, produce a short migration assessment containing:

```text
current frontend
current backend
current persistence mechanism
current authentication status
current job-fetching mechanism
current background processes
where resume/profile context is stored
all secrets/environment variables
features incompatible with free serverless hosting
```

Then implement the migration incrementally.

Prefer adapting the current architecture over replacing it.

After implementation, provide:

```text
1. files changed
2. database migrations created
3. environment variables required
4. Supabase setup steps
5. Vercel/Cloudflare deployment steps
6. GitHub Actions setup
7. security checks performed
8. two-user isolation test results
9. remaining limitations
10. exact command/checklist for going live
```

Do not declare the migration complete until two independent accounts have been tested and cannot access each other's private data.
