# Job Hunter project context

This document is the durable handoff for maintainers and future development sessions. It describes the product as implemented, the trust boundaries that must remain intact, and the checks required before distributing a build. It contains no user profile, credentials, resume text, or other personal data.

## Product intent

Job Hunter is a local-first career workspace for one person per installation. It discovers public job postings, ranks them against a user-maintained profile, keeps a review shortlist, prepares evidence-grounded application assets, and tracks progress. It is not a hosted multi-user service. Each tester runs an independent copy and owns a separate `data/` directory.

The product name is **Job Hunter**. The core promise is: focus the search, explain the match, preserve the user's verified facts, and keep the user in control of every external application or message.

## Main workflow

1. The user creates a profile manually or uploads one or more resumes.
2. A resume upload is parsed locally into an editable profile draft. It never silently overwrites the saved profile. Missing or ambiguous facts remain blank and require review.
3. Discovery reads public feeds, pages, or employer-board APIs. It caches bounded requests and reports blocked sources explicitly. Saved, reviewing, deleted, and already-seen postings are not re-added as new opportunities.
4. Profile fit and resume-text similarity are separate signals. Profile fit ranks opportunities; resume similarity recommends the best uploaded version.
5. New opportunities live in the New list. Moving one to Reviewing removes it from New and starts Application Studio generation in the background.
6. Application Studio stores versioned kits per job: ATS resume, cover letter, LinkedIn note, referral message, contact-search leads, and saved application-question answers.
7. The user reviews and edits every output. External form submission and LinkedIn messaging remain explicit user actions.
8. Deleting an opportunity removes its generated kits, answers, prepared documents, selection, and derived job caches. The listing can be restored, but its generated assets must be recreated. Deleting an uploaded resume removes its original and extracted text while retaining the saved profile and existing job kits.

## Architecture map

- `frontend/`: Next.js application. The main workspace is `frontend/src/app/page.tsx`; larger flows live under `frontend/src/components/`.
- `backend/main.py`: FastAPI lifecycle, profile/config, discovery, application states, review queue, deletion, preparation, and extension context.
- `backend/studio_api.py`: versioned Application Studio generation, editing, downloads, job workspace state, retries, and saved question answers.
- `backend/resume_api.py`: upload, local extraction, keyword indexing, rename/delete, profile drafts, and resume matching.
- `backend/database.py` and `schema.sql`: SQLite access and persistent tables.
- `backend/agents/`: job discovery/orchestration, document preparation, coaching, and optional submission.
- `backend/services/`: matching, job intelligence, language detection, resume intake, career generation/validation, rendering, and Studio storage.
- `extension/`: optional Chrome extension. It fills reviewed contact fields and can capture one visible LinkedIn hiring post for user-reviewed import.
- `assets/`: immutable prompt/reference documents and the fixed resume template.
- `tests/`: isolated tests using temporary databases and synthetic identities.
- `data/`: ignored local state. Never commit or include it in a tester archive.

## Persistent application states

`DISCOVERED` and `MATCHED` are new opportunities. `REVIEWING`, `QUEUED`, and `TAILORED` belong to the review/preparation phase. `APPLIED`, `INTERVIEWING`, `OFFER`, and `REJECTED` are pipeline states.

`studio_kits` indexes immutable kit versions by job. `studio_runs` holds the current background generation token and state (`queued`, `running`, `ready`, `needs_input`, or `failed`). Generation writes to `data/kits/.pending/` and publishes only after the job and token are revalidated under the queue lock. This prevents a deleted job from being resurrected by an in-flight generator.

## Data and privacy boundaries

- The API binds to localhost in supported launch paths and rejects untrusted origins and hosts.
- Chrome extension API access requires its exact ID in `TRUSTED_EXTENSION_IDS`.
- `.env`, `data/`, databases, uploads, generated artifacts, logs, PDFs, DOCX files, models, and private review notes are ignored by Git.
- Never log prompt bodies, profile content, resume text, form answers, cookies, passwords, or verification codes.
- Passwords and verification codes stay in the user's browser. The project does not store job-board credentials.
- Do not bypass login, CAPTCHA, robots controls, access blocks, or rate limits. Prefer official feeds/APIs and public structured data. A blocked site remains a manual/browser-assisted source.
- LinkedIn post capture is user initiated and limited to the visible post. It does not crawl a feed, enumerate connections, send requests, or claim that a suggested person is a verified employee or hiring manager.
- Generated claims, metrics, employers, tools, and dates must be traceable to the saved profile. Missing facts stay visible.

## Generation rules

Base instructions live in `assets/ATS_Resume_Prompt_Instruction.md`, `assets/Cover_Letter_Structure_Guide.md`, and `assets/LinkedIn_Referral_Message_Guide.md`. The fixed resume format is `assets/Resume template.pdf`.

- Resume: clean ATS-compatible Markdown, one-page rendered PDF, 400–750 words, XYZ-style bullets where the source evidence supports them, and zero fabrication.
- Cover letter: header, salutation, four paragraphs, sign-off, and 250–400 words.
- Connection invite: fewer than 300 characters.
- Referral message: 75–125 words, exact job title, requisition ID, evidenced skill match, public resume/portfolio URL, and a low-pressure close.
- Application answers use verified profile/story evidence and are stored with their kit.

## Discovery and matching rules

Each source must have bounded requests, timeouts, caching, stable source URLs, useful availability errors, and synthetic parser tests. A successful HTTP response without readable jobs is not a successful source result. Known blocked/sign-in-only sites stay in the board directory for manual use and out of automatic search.

Deduplication uses canonical job URLs and content/company/title fingerprints. Discovery history includes excluded jobs so identical repeated searches do not waste requests or create duplicates. A changed posting or changed criteria may be reconsidered. Jobs already in Reviewing or with a Studio kit are protected from discovery updates.

Posting language describes the advertisement text and is separate from required-language eligibility. Short or uncertain text must show `Unknown`. Posting time must distinguish source-provided time from Job Hunter's first-seen time. Visa sponsorship is evidence-based and may remain unknown.

`max_posting_age_days` is an optional saved preference and per-search override. When active, discovery accepts only postings with a valid source date inside the selected window; unknown dates are excluded with an explicit report reason. It never deletes or moves an existing saved/reviewing opportunity. Do not substitute first-seen time for an unknown source posting date.

## Local AI and external services

The base product works without a paid model key. Ollama is optional. Model output is treated as a draft and passes the same deterministic validators. ChatGPT subscriptions do not provide OpenAI API access. OpenRouter or other cloud providers require an explicit future integration, separate user credentials, clear data-sharing disclosure, and opt-in configuration.

Do not add a model merely because it is advertised as free. Confirm its current license, API terms, privacy behavior, context limits, structured-output reliability, and rate limits before exposing it. Never put provider keys in source control.

## Required checks before a release

Run from the repository root:

```sh
.venv/bin/python -m pytest -q
npm --prefix frontend run build
node --test frontend/tests/*.test.mjs
docker compose config
docker compose -f docker-compose.yml -f compose.ai.yml config
```

For the full browser suite:

```sh
RUN_BROWSER_TESTS=1 .venv/bin/python -m pytest -q
```

Then review `git diff --check`, `git status --short`, the staged diff, dependency audits when dependencies changed, and a source/privacy scan for emails, tokens, local absolute paths, real resumes, and database files. Browser tests must use synthetic profiles and temporary storage. Visually inspect the main pages at desktop and narrow widths after UI changes.

## Distribution rule

Publish source-controlled files only. A tester release must not be created by zipping the developer's working folder. A clean clone must start without a profile, credentials, resume, application history, or generated kit. Keep the localhost deployment and one-installation-per-person guidance prominent unless authentication, tenant isolation, storage encryption, CSRF strategy, and hosted operations are deliberately designed and reviewed.
