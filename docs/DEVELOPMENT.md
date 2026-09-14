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

Use an official public API/feed where available. Implement and register adapters in `backend/agents/job_sources.py`, update the discovery UI's source options and add parser/filter tests with synthetic fixtures. Include bounded requests, timeouts, caching, useful errors, source URLs and deduplication. Distinguish fetched jobs from matching jobs. Do not turn access failures into successful empty caches, claim a directory link is an integration, or add cookies/credentials to code.

## Share changes

Never commit `data`, `.env`, personal resumes, screenshots with private details, downloaded models or browser sessions. Run `git status --short` and review `git diff --cached` before committing. Follow [privacy guidance](PRIVACY.md). Use your own Git identity and GitHub authentication; neither is bundled with this project.

The current app is intended for separate local installations. Converting it into hosted multi-user software requires architectural changes; changing host/port settings alone does not provide user isolation.
