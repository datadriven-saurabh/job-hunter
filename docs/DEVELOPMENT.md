# Developer guide

## Layout

- `frontend/`: Next.js UI and TypeScript components.
- `backend/main.py`: FastAPI application and application workflow routes.
- `backend/database.py`: local SQLite persistence.
- `backend/agents/`: discovery adapters, orchestration, local-model calls and optional submission.
- `backend/services/`: profile matching, resume indexing, one-page rendering and outreach drafts.
- `backend/studio_api.py`, `backend/model_api.py`: Application Studio and model comparison endpoints.
- `extension/`: optional Chrome autofill extension.
- `tests/`: isolated backend workflow tests.
- `scripts/local.py`: native service launcher.

See [native setup](NATIVE_SETUP.md) for dependencies. For UI development use `npm --prefix frontend run dev` alongside the API, after stopping the production frontend on port 3000.

## Check changes

```sh
.venv/bin/python -m pytest -q
npm --prefix frontend run build
docker compose config
docker compose -f docker-compose.yml -f compose.ai.yml config
```

On Windows replace the Python executable with `.\.venv\Scripts\python.exe`. Tests use temporary database storage; do not point tests at a user's live database. A successful frontend build includes TypeScript validation. Test actual PDFs visually when changing resume layout and verify they remain one page.

## Add a source

Use an official public API/feed where available. Implement and register adapters in `backend/agents/job_sources.py` and add parser/filter tests with synthetic fixtures. The discovery UI reads the registered source catalog automatically. Include bounded requests, timeouts, caching, useful errors, source URLs and deduplication. Distinguish fetched jobs from matching jobs. Do not turn access failures into successful empty caches, claim a directory link is an integration, or add cookies/credentials to code.

## Share changes

Never commit `data`, `.env`, personal resumes, screenshots with private details, downloaded models or browser sessions. Run `git status --short` and review `git diff --cached` before committing. Follow [privacy guidance](PRIVACY.md). Use your own Git identity and GitHub authentication; neither is bundled with this project.

The current app is intended for separate local installations. Converting it into hosted multi-user software requires architectural changes; changing host/port settings alone does not provide user isolation.

## Security checks

Python dependencies are bounded by `requirements.txt` and pinned in `constraints.txt`; JavaScript uses `frontend/package-lock.json`. After a planned upgrade, run the tests, regenerate constraints in a clean Python environment, and audit both sets with `pip-audit -r requirements.txt` and `npm --prefix frontend audit`. Install the PyPA `pip-audit` tool in a separate audit environment. Never copy a developer virtual environment into a tester release. See [review scope and limitations](SECURITY_REVIEW.md).

## Full browser regression run

```sh
npm --prefix frontend run build
RUN_BROWSER_TESTS=1 .venv/bin/python -m pytest -q
node --test frontend/tests/*.test.mjs
```

The browser suite starts its own frontend and API on temporary localhost ports with a synthetic database. All employer navigation is blocked. It exercises real HTTP resume upload, preparation, Studio, coaching, deletion/restoration and pagination. Its expanded CORS origin exists only in the test wrapper, not in the distributed API.

Source availability: `/api/v1/jobs/sources` returns active automatic sources. Add `?include_unavailable=true` to include the manual directory and availability reasons. Confirmed unavailable sites are documented in `MANUAL_ONLY`; fresh access blocks use a per-source one-hour suspension in the local cache. Keep blocked sites out of automatic selection, retain existing opportunities and never mistake HTTP success for successful job extraction.
