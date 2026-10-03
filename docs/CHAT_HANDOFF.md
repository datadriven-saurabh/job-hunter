# Job Hunter — chat handoff

Updated: 24 September 2026. This file summarizes the development conversation and the last verified state. It contains no credentials, resume contents, or private profile data. Read the current code and Git status before making changes; earlier requests below are historical context, not proof that every feature was fully verified.

## Start here in the new chat

Suggested opening request:

> Read docs/CHAT_HANDOFF.md and docs/DISCOVERY.md. Continue the pending live verification of Job Hunter's background job discovery and new-user signup. Preserve unrelated uncommitted changes, use only free services, and never expose credentials or personal data. Check the current deployment before changing code.

## Product and user priorities

Product name: **Job Hunter**. A professional, approachable career workspace for discovering jobs, matching a candidate profile, prioritizing applications, managing multiple resumes, and preparing application documents. The project began as local-first software but now also has a hosted deployment for multiple users.

The user prioritizes a working end-to-end product, low latency, clear progress, privacy, tenant isolation, novice-friendly instructions, and zero-cost operation. They previously authorized pushing project changes to GitHub and deployment. Do not introduce paid infrastructure or paid model calls. Do not publish local data, credentials, generated documents, or personal profile details.

An API key was pasted earlier in the conversation. It is deliberately omitted here. Treat it as exposed; do not reproduce it, place it in source, or infer that it is safe to reuse. Review secure configuration separately if model work resumes.

## Workspace, repositories, hosting

- Working directory: `/Users/saurabh/Desktop/codex-projects/job-finder`
- Source repository: `git@github.com:datadriven-saurabh/job-hunter.git`
- Production repository: `git@github.com:datadriven-saurabh/job-hunter-live.git`
- Production checkout used during this session: `/private/tmp/job-hunter-live-deploy` (temporary; verify it still exists).
- Frontend: https://job-hunter-live-six.vercel.app
- Backend: https://job-hunter-live.onrender.com
- Render service: `job-hunter-live`, ID `srv-dan9om8ae00c73e1bum0`
- Authentication/database provider: Supabase. Public auth configuration is served by backend `/auth-config`; do not dump private environment files or tokens.
- Root `.vercel/project.json` contains the Vercel project linkage.
- Production repo pushes trigger Vercel/Render builds. Source repo pushes alone are not proof of a production deployment.
- Verified Git author used for deployment: `datadriven-saurabh <126279386+datadriven-saurabh@users.noreply.github.com>`; earlier author mismatch could block Vercel.

## Important documentation caveat

`docs/PROJECT_CONTEXT.md` contains useful architecture details but also stale statements that the app is exclusively local and not multi-user. Hosted authentication/database code and current deployment supersede those claims. It also contains uncommitted OpenRouter descriptions that must not be assumed deployed. Do not blindly overwrite that file or treat it as authoritative about release status.

Other useful references: `docs/DISCOVERY.md`, `docs/PUBLIC_DEPLOYMENT.md`, `docs/PRIVACY.md`, README, and the instruction files under `assets/`.

## Architecture map

- Next.js/React frontend under `frontend/`; workspace and components implement opportunities, profiles, resumes, review, Studio and settings.
- FastAPI entrypoint: `backend/main.py`.
- Database and user context: `backend/database.py`; local SQLite and hosted PostgreSQL/Supabase paths.
- Job adapters/catalog: `backend/agents/job_sources.py`.
- Bounded source executor: `backend/services/discovery_fetch.py`.
- New asynchronous discovery lifecycle: `backend/services/search_runs.py`.
- Skill summaries: `backend/services/skill_trends.py` and frontend SkillTrends component.
- Matching/intelligence/generation: `backend/services/` and `backend/agents/`.
- Resume APIs: `backend/resume_api.py`; Studio APIs: `backend/studio_api.py`.
- Optional Chrome extension: `extension/`.
- Tests use synthetic profiles and temporary databases; never test by publishing private candidate data.

## Historical requested functionality

Much of this is implemented, but do not claim comprehensive live verification without checking:

- Calendar date inputs; multiple uploaded resumes with rename/delete, parsing into an editable profile draft, keyword indexing and best-resume suggestions.
- Public job feeds/pages with source attribution, posting date/freshness filters, posting language and evidence-based visa sponsorship detection.
- Profile matching and application prioritization; sorting/filtering by score, date, source and location.
- Bulk opportunity deletion, a separate Reviewing phase, deduplication across new/reviewing/deleted jobs, automatically preparing Studio on review, persisted per-job generated assets and cleanup on job deletion.
- One-page ATS resume, cover letter, LinkedIn invite/referral drafts and application-question answers based on the candidate's verified facts and target JD/link.
- LinkedIn contact suggestions are leads, not verified employee relationships. Visible-post import is user initiated; do not silently crawl private feeds or send messages.
- Skill demand summaries for similar saved jobs: evidence counts and links, role-family/date grouping; not a claim about the entire job market or a proven time-series growth trend.
- Professional, more colorful UI, discovery action on Opportunities, reduced repetitive header/status UI.
- Security/privacy review, README and tester setup instructions, hosted deployment and optional free models.

Requested source history includes RemoteOK, We Work Remotely, Remotive, Hacker News, YC, LinkedIn, HiringCafe, Wellfound, BuiltIn, AIJobs.net, Indeed, Glassdoor, Google Jobs, Stepstone, GermanTechJobs, Otta, Relocate.me, Berlin Startup Jobs, EU-Startups, JobFluent, Startup.jobs, VC talent boards, Working Nomads, Hyrise, VanHack, Jobbatical, Honeypot, Landing.jobs, EURES, Work in Finland and Make it in Germany. This is a wishlist/history, not a supported-adapter list. Inspect the source catalog for actual availability. Employer-specific ATS services such as Greenhouse/Lever/Ashby/SmartRecruiters require a company identifier and are excluded from generic automatic discovery.

## Document-generation constraints

Read the actual assets before changing generation:

- `assets/ATS_Resume_Prompt_Instruction.md`
- `assets/Cover_Letter_Structure_Guide.md`
- `assets/LinkedIn_Referral_Message_Guide.md`
- `assets/job_hunter_ai_optimization_plan.md`
- `assets/resume_format_agent_instructions.md`
- `assets/job_application_answering_agent_requirements.md`
- Fixed resume layout: `assets/Resume template.pdf`

Zero fabrication: no invented metrics, employers, dates or tools. Resume target 400–750 words, ATS-safe Markdown and evidenced XYZ bullets. Cover letter 250–400 words and four main paragraphs. Invite notes <300 characters. Post-connection referral messages 75–125 words, exact role, job ID, skill match and resume/portfolio link or explicit missing-input placeholder, with a low-pressure close. Missing evidence must remain missing rather than being invented to satisfy formatting.

## Latest task and implemented changes

Problem: selecting many sources caused a frontend timeout/error, although backend processing continued and jobs appeared later.

Latest requested changes: optimize the flow, cap selected boards, remove unsupported automatic sources, ten-minute fetch cooldown with feedback, loading indicators, timing-based source ranking and a combined one-minute estimated budget, and verify signup.

Implemented and pushed:

1. `POST /api/v1/jobs/search-runs` returns HTTP 202 and a run ID; `GET /api/v1/jobs/search-runs/{id}` returns owner-scoped progress. Legacy live `/jobs/search` also starts a run; demo remains synchronous.
2. Hard cap of three distinct boards; unsupported/company-board sources rejected on backend as well as excluded from automatic UI choices.
3. Ten-minute successful-source cooldown per user, including successful fetches with zero matches. UI displays countdown and cooldown toast; server enforces it.
4. Measured source durations include fetch, matching and saving. Catalog ranks availability/speed and rejects combined estimates >60 seconds. Unmeasured source default is 20 seconds. This is an admission estimate, NOT a guaranteed runtime deadline.
5. Two background search workers per server process, one active run per user; capacity exhaustion returns a useful error. Sources in a run execute sequentially and save progress/results per board.
6. Run/timing records persist in `source_cache` under owner-qualified keys. Source metrics load in one database query instead of one query per board.
7. Frontend remembers run ID in sessionStorage, polls every three seconds without overlapping requests, resumes when dialog reopens, shows spinner/progress and handles stale/missing runs. Cooldown display decrements locally.
8. Added loading feedback to discovery, generic dashboard actions and authentication; this was not a complete audit of every background process in the product.
9. Regression tests updated to distinguish synchronous worker behavior from the asynchronous HTTP contract; new tests cover limits, cooldown, timing budget, progress persistence, unavailable boards, active-run reuse and stale runs.

Known limitations:

- Worker concurrency/active-run reservations are process-local, not a distributed durable queue.
- A restart can interrupt work. Progress older than five minutes is shown as interrupted; an exceptionally slow live run can also hit that threshold.
- Source fetch deadline is bounded, but underlying timed-out fetch threads can finish later; matching/database work is not a strict 60-second deadline.
- A source whose estimate exceeds 60 seconds cannot be selected until timing is changed/reset; no sophisticated adaptive recovery was implemented.
- Cold starts and external source failures remain possible on free hosting.
- No completed authenticated live search was verified in the last session.

## Recent commits

Source repo:

- `ed0f4a5`: evidence-backed skill summaries.
- `5a381ef`: background discovery, budgets, cooldown, progress.
- `f09a579`: fewer database calls and asynchronous lifecycle verification.
- `fe9fe95`: discovery operating/verification documentation.

Production repo:

- `44ce8fe`: skill summaries.
- `55401ba`: initial background-discovery changes.
- `2f52251`: latest discovery refinements and tests.

The final documentation-only source commit was not copied to production during the last turn. Verify current remote state rather than assuming these remain the latest commits.

## Last verification results

- 31 targeted tests passed across search runs, source executor, product review, resumes/sources and Stepstone; then the expanded search-run file passed all three tests after an additional lifecycle test was added.
- `npm --prefix frontend run typecheck` passed.
- `npm --prefix frontend run build` passed.
- `git diff --check` passed.
- Vercel CLI reported latest production deployment Ready.
- Served dashboard assets contained the new “Maximum 3 boards” UI.
- Backend `/health` returned HTTP 200.
- `/auth-config` returned HTTP 200.
- Hosted `/signup` returned HTTP 200.
- Supabase public settings showed signup enabled, email provider enabled, and email confirmation required.
- These are NOT proof of completed signup/email delivery or a successful authenticated job search. No account was created during those checks.

## Immediate pending work

1. User was asked to sign in directly in Chrome at the live app and reply “ready”. Chrome showed the login page, with no active Job Hunter session. Never ask them to paste a password into chat.
2. Once signed in, verify a real single-board search end to end: 202 start, progress, close/reopen dialog, final report, populated opportunities, cooldown and repeat-search behavior. Observe browser errors if it fails; distinguish API/auth/CORS/backend availability from source blocks.
3. Verify three-board cap and estimated budget in UI as well as server tests. Confirm no duplicate jobs, and existing Reviewing jobs remain intact.
4. Finish new-user signup verification with a user-controlled test identity and email confirmation. Public settings alone are insufficient to call account creation fully working.
5. If necessary, inspect Render build/logs to confirm the latest backend deployment specifically, since health 200 alone does not identify its commit.
6. Visitor analytics was requested earlier but Vercel Analytics integration was NOT implemented in the recorded work. Region migration to Singapore was also NOT completed. Do not claim either is done.
7. Optional embeddings download, broader automated browser tests, and full feature/security audit remain historical follow-ups unless verified elsewhere.

## Preserve current uncommitted work

At handoff, these tracked files were modified outside the staged discovery work:

- `.env.example`
- `README.md`
- `backend/ai/router.py`
- `config/ai.json`
- `docs/PRIVACY.md`
- `docs/PROJECT_CONTEXT.md`
- `docs/PUBLIC_DEPLOYMENT.md`
- `render.yaml`
- `tests/test_career_engine.py`
- `tests/test_hosted_deployment.py`

They include substantial OpenRouter integration work. Do not discard, blindly stage, copy to production, or describe it as deployed. Review separately. The user's requirement is free-only usage with secure server-side keys and no unapproved sharing of profile data. ChatGPT subscription access is not an API key.

## Useful verification commands

```sh
git status --short
git log -5 --oneline
PYTHONPATH=. .venv/bin/pytest tests/test_search_runs.py tests/test_discovery_fetch.py tests/test_product_review.py tests/test_resumes_sources.py tests/test_stepstone.py -q
npm --prefix frontend run typecheck
npm --prefix frontend run build
git diff --check
```

Use current browser/tool documentation for UI operations. Use fresh accessibility state after actions. Do not extract session tokens or read browser credential storage to work around sign-in. Preserve existing signed-in sessions. No CAPTCHA/access-control bypass, private-feed scraping, automatic external messages or paid upgrades were authorized by the latest task.
