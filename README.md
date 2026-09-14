# AutoCareer-AI

A local career workspace built from `job-hunter-architecture.md`: Next.js dashboard, FastAPI API, SQLite/SQLAlchemy persistence, LangGraph discovery workflow, Typst resumes, Playwright application worker, and Manifest V3 Chrome extension.

## This Mac: configured local runtime

Ollama is installed inside `.runtime/ollama/` (official v0.34.0 archive, SHA-256 verified). Qwen3 4B is stored in `data/ollama-models/`. Playwright Chromium is installed in the standard user cache. `.env` enables local AI and headless submission, and the saved preferences enable headless applications.

Start all three services, independently of Codex:

```sh
.venv/bin/python scripts/local.py start
```

Check or stop services launched by this script:

```sh
.venv/bin/python scripts/local.py status
.venv/bin/python scripts/local.py stop
```

Logs are in `data/runtime/`. No login item is installed; run the launcher again after reboot. Chrome extension files and autofill tests are ready in `extension/`. Loading into the personal Chrome profile is still pending: computer-control permissions now work, but Chrome stopped exposing window controls during directory selection. In `chrome://extensions`, use Load unpacked and choose this project’s `extension` directory, not the project root.

The dashboard shows local-model, browser, and profile readiness. Preparation never submits. For a live eligible role, prepare/download/review your documents, then check the review acknowledgment and select **Submit application**. Demo roles and placeholder profile details are blocked from submission. Real employers can still require browser assistance.

## Run locally

Requires Node.js 20.9+ and Python 3.9+ (Python 3.11+ recommended).

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
npm --prefix frontend ci
```

Start the API from the repository root:

```sh
.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```sh
npm --prefix frontend run dev
```

Open **http://localhost:3000**. API documentation is at **http://localhost:8000/docs**.

Production frontend: `npm --prefix frontend run build`, then `npm --prefix frontend run start`.

Alternatively, `docker compose up --build` starts both services with loopback-only published ports. SQLite and generated documents persist under `data/`. The application is a single-user local edition, not an authenticated public service.

## First use

1. Choose **Explore demo workspace** for eight clearly labeled sample opportunities and a fictitious profile. Demo jobs can never trigger external submissions. Loading the demo does not overwrite an existing profile.
2. Open **My profile** and replace the sample details, skills, resume, experience, and education with your own facts.
3. Set **Preferences** for roles, locations, required skills, exclusions, salary, and daily limits. Empty location filters allow any location. Salary filters exclude known salaries below your threshold; listings with undisclosed salaries remain visible.
4. Choose **Find opportunities** and search LinkedIn, Remotive, Remote OK or We Work Remotely; select a public Greenhouse, Lever or Ashby board slug, or import a posting by pasting its URL and description. Discovery filters and scores jobs, classifies their application path, and deduplicates by URL.
5. Upload PDF, DOCX or TXT resume variants in **My documents**. Select roles and **Prepare applications**, review the recommended source resume for each job, then prepare. Download each resume PDF and cover letter from **My documents** or the detail panel.
6. Use **Applications** to track review, submission, interviews, offers, and archived applications. **I submitted this** records your manual confirmation; it does not submit a form.
7. Practice behavioral, technical, and system design questions in **Interview coach**.

## What runs without a model

The complete review workflow runs without API keys. Job priority uses weighted evidence from the current profile: recognized job skills, target role alignment and general experience, with explicit review flags. This is a transparent heuristic, not a semantic embedding model or hiring probability. Job filters run before scoring; see Application prioritisation below.

Tailoring ranks verified skills and source bullets by job relevance, then compiles an ATS-readable, single-column PDF using Typst. Source bullets retain their original wording and metrics: the product does not fabricate missing XYZ achievements. A grounded cover letter is provided as editable text. To obtain strong XYZ bullets, supply accomplishment, measured result, and method in your base profile.

The default coach generates role-specific template questions and checks rubric coverage using explicit language cues. Its score measures rubric coverage, not interview success or a semantic assessment of technical correctness.

## Optional local model

Install and run Ollama separately and pull the model you intend to use. The configured model is `qwen3:4b`; change the reasoning model and local URL through the configuration API if needed.

```sh
ENABLE_LOCAL_LLM=true .venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

The optional adapter calls the configured Ollama loopback endpoint. It can rank exact source bullets and generate structured interview questions and feedback. Pydantic validates question and feedback outputs; ranking can select only existing source bullets. Model/network errors are reported rather than silently claiming AI output. The dashboard displays the configured model and identifies local AI feedback. Hosted Gemini generation is not wired; the architecture's `primary_model` field is retained for compatibility. No cloud model credentials are required or used.

## Browser-assisted applications

In Chrome, open `chrome://extensions`, enable Developer mode, and load the `extension/` folder with **Load unpacked**. The extension is not installed automatically.

Open a saved live job's exact application URL, then open the extension popup and choose that job. **Fill this application** populates only visible empty contact fields on that matching URL; existing answers remain untouched. Download and attach the prepared resume manually, review answers, complete any authentication/CAPTCHA yourself, and submit. The extension never submits. It uses `activeTab` access and injects only after a user click, rather than watching every website.

## Optional headless submission

Document preparation always stops for review. Actual submission requires an explicit `submit=true` request after document review, and both conditions must be true:

- The saved **Enable eligible headless applications** preference is on (configured on this Mac).
- The API is started with `ENABLE_LIVE_SUBMISSION=true` (loaded from the local `.env`).

Install the browser runtime first:

```sh
.venv/bin/playwright install chromium
```

Only recognized Lever/Greenhouse hosts, above-threshold matches, and applications within the daily limit are eligible. The worker fills common contact fields, attaches a resume, checks for authentication/CAPTCHA, and seeks a unique submit button. It marks `APPLIED` only after an explicit success message. Unsupported forms and unconfirmed outcomes are logged for review. An unconfirmed submission is blocked from automatic retry to prevent duplicates.

This is a conservative generic adapter, not a guarantee of compatibility with every employer form. No external applications were submitted during development or verification. Live submissions and the extension require validation against your intended employers. Chromium execution is tested against a local form with all network requests blocked; required unanswered fields stop submission. The optional self-patching Meta-Agent is not included.

## Validation

```sh
.venv/bin/python -m pytest -q
npm --prefix frontend run build
node --check extension/content.js
node --check extension/popup.js
RUN_BROWSER_TESTS=1 .venv/bin/python -m pytest -q
.venv/bin/python -m scripts.verify_local_ai
```

API tests use an isolated temporary database. They cover discovery/deduplication, filters and classification, preparation, PDF bytes, extension context, invalid status transitions, retry protection, interview feedback, origin rejection, missing resources, and queue validation. Browser checks cover demo onboarding, application preparation, documents, coaching, and responsive layout.

## API surface

- `GET /health`
- `GET/POST /api/v1/profile`
- `GET/POST /api/v1/config`
- `POST /api/v1/demo`
- `GET /api/v1/jobs/sources` — supported public adapters
- `POST /api/v1/jobs/search` — provider, sources (optional list), board, keywords, location, limit, page_url
- `POST /api/v1/jobs/import` — job title, company, HTTPS URL, description, location
- `GET /api/v1/applications?status=MATCHED`
- `POST /api/v1/applications/batch-apply` — JSON array of job IDs; prepares documents
- `POST /api/v1/applications/batch-apply?submit=true` — explicitly submit reviewed, eligible applications
- `GET /api/v1/runtime` — model, browser, and profile readiness
- `PATCH /api/v1/applications/{job_id}` — `{ "status": "APPLIED" }`
- `GET /api/v1/applications/{job_id}/document/resume`
- `GET /api/v1/applications/{job_id}/document/cover-letter`
- `GET /api/v1/extension/fill-context/{job_id}`
- `POST /api/v1/interview/generate-questions?job_id=...`
- `POST /api/v1/interview/evaluate` — `{ "job_id": "...", "question_id": "...", "answer": "..." }`

All profile/config operations use user ID `local`. SQLite and documents stay in `data/` (override with `DATA_DIR`). Application workers are process-local: run one API worker. Interrupted queued work returns to `MATCHED` at startup. No automatic background schedule is installed.

## Project layout

- `schemas.py`, `schema.sql`: domain models and database schema
- `backend/database.py`: local persistence
- `backend/agents/`: Scout, Classifier, Tailor, Apply, Coach, optional Ollama adapter, and LangGraph workflow
- `backend/templates/`: Typst resume template
- `backend/main.py`: API, validation, status transitions, and document downloads
- `frontend/src/app/`: responsive workspace interface
- `frontend/src/lib/api.ts`: typed fetch client
- `extension/`: Chrome bridge
- `tests/`: workflow verification

Implementation references: [LangGraph graph API](https://docs.langchain.com/oss/python/langgraph/graph-api), [Next.js App Router](https://nextjs.org/docs/app/getting-started), [Typst documentation](https://typst.app/docs/).

## Resume library and discovery updates

Experience dates use native month calendars where supported, with month/year dropdowns in other browsers. Graduation uses a year dropdown. Invalid or reversed dates are rejected.

Upload several PDF, DOCX or UTF-8 TXT resumes (10 MB each) in My documents. Extraction, originals and the top-60 keyword corpus remain local. Scanned PDFs need OCR before upload. The profile resume remains available separately. Renaming and original downloads are supported. Before preparation, TF-IDF lexical similarity recommends a source resume and exposes matching keywords. Scores describe text similarity, not hiring probability; short descriptions are flagged. Users can override the recommendation. Uploaded PDF originals are preserved; DOCX/TXT content is rendered as a PDF without blending facts across versions. Changing a selected resume invalidates prepared documents; submitted/queued choices are locked.

Resume APIs: GET /api/v1/resumes; POST /api/v1/resumes/upload (multipart file, optional label); GET/PATCH /api/v1/resumes/{id}; GET /api/v1/resumes/{id}/download; GET /api/v1/applications/{id}/resume-matches; POST /api/v1/applications/{id}/resume with resume_id.

Public discovery supports LinkedIn guest listings (up to 25), Remotive, Remote OK, We Work Remotely RSS, and company boards from Greenhouse, Lever and Ashby. The HiringCafe structured-page adapter reports access failures; live verification returned HTTP 403. Multi-board search preserves partial successes and shows errors per source. Original source links and attribution are retained. Remotive, Remote OK and WWR full feeds are cached for six hours. LinkedIn detail retrieval is bounded to two concurrent requests. Other results/errors are cached for fifteen minutes.

The board directory also links to Hacker News, YC Work at a Startup, Wellfound, Built In, AIJobs.net, Indeed, Glassdoor, Google Jobs, Workable and SmartRecruiters. These are browser/manual-import entries, not implemented scraping integrations. Account logins remain in the browser; the app stores no board passwords/cookies and does not claim to verify browser sessions.

Official feed references: [Remote OK](https://remoteok.featurebase.app/help/articles/3140840-is-there-an-api-or-rssjson-feed-of-remote-jobs), [We Work Remotely](https://weworkremotely.com/remote-job-rss-feed), [Remotive](https://github.com/remotive-io/remote-jobs-api), [Ashby](https://developers.ashbyhq.com/docs/public-job-posting-api).

## Application prioritisation

Saved jobs now recompute their fit whenever they are read, using the current saved profile and preferences. Application status and documents are preserved. The dashboard sorts by this current score, displays a priority label, and explains each job in **Why this job ranks here**. Resume selection remains a separate text-similarity comparison between uploaded versions.

The transparent local heuristic weights recognized job-skill coverage at 65%, target role alignment at 25%, and general experience at 10%. It reads profile achievements and summary as well as listed skills, normalizes known aliases (including SQL/MySQL), distinguishes explicitly preferred skills, and provides matching source excerpts. Unrelated additional profile skills do not lower coverage. Missing skills mean no evidence was found, not that the person lacks the skill. Overlapping dated experience is counted once. Unspecified experience receives a neutral component rather than an assumed match.

Priorities are Apply first (75+), Consider (55–74), Stretch / low fit (below 55), or Review details for sparse descriptions, preference conflicts, or detected language/geographic requirements needing verification. Seniority and experience gaps cap high scores. Unknown employment type no longer excludes a listing. Source reports show keyword candidates and exclusion reasons, not misleading total-download counts.

This is not an embedding/LLM semantic evaluator or a hiring probability. The finite skill vocabulary and English-oriented requirement rules cannot understand every qualification, alternative requirement, negation or language. Mandatory credentials, sponsorship and work eligibility require manual review. Weights are explicit defaults, not statistically calibrated predictions. Sources remain the reference for final decisions.

## Application Studio and one-page ATS format

Open **Application studio** or select **Create one-page resume, cover letter & referral drafts** on a job. Choose a saved opportunity or paste a public job URL. Review imported fields before generating; blocked pages, JavaScript-only pages and unsupported custom domains need a pasted description. URL retrieval uses fixed public-host allowlists, validates redirects and never forwards browser cookies.

The one-page layout follows the supplied reference's centered header and ruled Summary, Skills, Experience and Education sections. The reference itself is two pages; the implementation selects relevant existing bullets, joins obvious line-wrap fragments, preserves employer/title/date facts, checks PDF page count and never reduces text below 9.5pt. It fails clearly if content cannot fit legibly. Uploaded original resumes remain available unchanged; **Application Studio always uses My profile**, while standard preparation respects the selected uploaded original. No sample person's facts, invented metrics or unsupported skills are inserted.

Cover letters and referral messages are locally generated factual drafts. Edit and save them before downloading. The connection note is capped at 200 characters as a conservative drafting limit. These features do not send messages or connection requests. Contacts explicitly named in a job description appear with the source excerpt; LinkedIn search links suggest employees, recruiters and team leads. They are not verified connections or confirmed hiring managers. Check current employer, identity and relationship before contacting anyone.

Draft kits persist under data/kits. APIs: POST /api/v1/studio/resolve; GET/POST /api/v1/studio/kits; PATCH /api/v1/studio/kits/{id}; GET /api/v1/studio/kits/{id}/resume; GET /api/v1/studio/kits/{id}/cover_letter, connection_note, or referral_message.

## Additional discovery sources

Arbeitnow Europe and UK read up to two pages of their public API and cache the feed for six hours. SmartRecruiters accepts a company identifier, reads up to 200 posting cards and up to 25 relevant full descriptions with two concurrent requests. Original attribution links remain visible. Public source verification succeeded for all three adapters. These are bounded snapshots, not complete worldwide job indexes.

References: https://www.arbeitnow.com/blog/job-board-api and https://developers.smartrecruiters.com/docs/posting-api .

## Free local model comparison

**Model lab** lists models actually installed in Ollama, lets you select the active model, and runs three synthetic skill-evidence tests sequentially. Results show exact-case pass counts, latency, outputs and failures. The comparison includes missing skills, irrelevant profiles and an instruction-injection case. A good result on three tests does not establish superior general writing or reasoning quality.

This Mac has qwen3:4b, qwen2.5:1.5b and gemma3:1b. Other machines can install them with `ollama pull MODEL`. Models have no API usage fee but use local memory/storage and remain subject to their licenses. No cloud model keys are required. AI coaching uses the selected model; resume facts and priority rules remain deterministic. APIs: GET /api/v1/models; POST /api/v1/models/active; POST /api/v1/models/compare; GET /api/v1/models/comparison.

## Sharing the source

The source repository excludes .env, local databases, uploaded resumes, generated drafts/PDFs, personal LinkedIn notes, downloaded models and dependency folders. Copy .env.example to .env for a new local installation. The supplied reference PDF is also excluded; the implemented Typst layout is included. Never commit data/ or generated personal documents to publish the app.
