# Background job discovery

Automatic searches use POST /api/v1/jobs/search-runs and poll the owner-scoped
GET /api/v1/jobs/search-runs/{id}. The legacy search route also starts a run.
Maximum three public boards and estimated combined duration <=60s are enforced
server-side. Company-board adapters remain in the manual directory. Successful
sources cool down for 600s per user. Timing measures fetching plus matching and
saving; it is an estimate, not a completion guarantee. Run records and timing are
stored in source_cache with owner-qualified keys. Execution uses two background
threads on the current server, with one active run per user. A server restart may
interrupt a run; stale progress is marked interrupted after five minutes. This is
not a distributed durable worker queue. The browser remembers the run in session
storage and resumes polling when the discovery dialog is reopened.

## Verification

Run `PYTHONPATH=. .venv/bin/pytest tests/test_search_runs.py tests/test_discovery_fetch.py tests/test_product_review.py tests/test_resumes_sources.py tests/test_stepstone.py -q` and `npm --prefix frontend run build`.

For a hosted smoke test, sign in, choose one public board, start discovery, close and reopen the dialog, and verify progress resumes. Once finished, verify new opportunities and the source cooldown. A new account must confirm its email before signing in when Supabase email confirmation is enabled.
