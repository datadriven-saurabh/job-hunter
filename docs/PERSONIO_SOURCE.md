# JA Solar Europe public employer feed

Validated 29 September 2026: public XML returned HTTP 200 with 10 positions including a Senior Business Analyst Europe role in Madrid. This is one employer, not an aggregate Personio search and not evidence of India or worldwide remote coverage.

Official feed documentation: https://developer.personio.de/v1.0/reference/get_xml
Employer feed: https://ja-solar.jobs.personio.de/xml?language=en

One fixed allowlisted GET, no credentials, no detail requests. Existing transport enforces 25-second request timeout and 12 MB response cap; parser additionally rejects documents above 2 MB, DTD/entity declarations, malformed XML and unexpected roots. At most 200 positions are inspected/returned. Existing discovery caches query results for 15 minutes and applies cooldown/admission limits. Access challenges remain errors. Attribution and numeric requisition IDs are retained. Keywords match title/description; normal downstream criteria handle geography. Empty valid feeds are allowed.

Personio createdAt is an ATS record creation time, not a verified posting time: it is deliberately not mapped to posted_at. Posting-age filters therefore exclude these records unless a publication date is added from a verified source later. Requesting English does not prove every description is English. Missing descriptions are flagged incomplete. Feed availability is point-in-time and all listings may not match the user's language/eligibility preferences.

Tests: PYTHONPATH=. .venv/bin/pytest tests/test_personio_feed.py tests/test_new_sources.py tests/test_search_runs.py -q

No GitHub push or deployment performed by the source-maintenance automation.
