# Product review — 16 September 2026

This review covers the local, single-person edition. Each tester must use a separate installation. It is not approval to expose the API or dashboard on the internet.

## Findings and fixes

- **Resume preparation:** recommendations could automatically select an upload that the strict template generator refused. Preparation now explicitly uses verified My profile facts. Upload comparison and original-file download remain available for manual applications. Unsupported selections are rejected before any part of a batch is queued.
- **Submission safety:** an application was marked ready before browser submission completed. It now remains reserved through execution. An unconfirmed attempt is recorded before the submit click, so a crash or timeout cannot silently enable another submission. Restart recovery retains reviewed documents and the review requirement.
- **Concurrent profile edits:** an older evidence editor could overwrite a newer profile. Both profile editors now send a revision; stale saves fail with a recovery instruction. Candidate evidence has a reload control. API callers that omit the revision retain the original unconditional-save behavior.
- **Browser readiness:** repeated runtime polling no longer launches synchronous Playwright drivers in worker threads. One bounded asynchronous probe runs at startup; missing browser setup does not prevent the rest of the app from starting.
- **Matching:** explicitly supplied language proficiency is used when checking language requirements. Separate required/preferred language clauses are handled independently; explicit “not required” skill statements are not gaps. Country aliases such as Germany/Deutschland/DE are normalized, and region matching uses an explicit country list without inferring work authorization. Matching remains a conservative heuristic with a finite vocabulary, not a hiring probability or a general semantic qualification assessment.
- **Edited drafts:** unsaved edits no longer show download actions for older saved text. User-edited assets display format-check and factual-review warnings.
- **Navigation:** all opportunities are accessible through pagination; Select all remains limited to the visible page. Public portfolio and GitHub URLs are editable in My profile. The summary field explains the 50–70-word requirement.
- **Extension:** exact-page verification now preserves job-identifying URL query parameters. Tracking parameters may differ, but one requisition cannot be confused with another on the same path.
- **Discovery:** searches report new opportunities and previously seen/duplicate postings separately. Saved and deleted jobs are skipped, source details are reused, and unseen candidates are prioritized before applying the result limit. Excluded jobs can be reconsidered when filters or posting content change. Tracking URLs are normalized without dropping requisition parameters.
- **Data access:** individual-job lookup no longer loads and rescores the entire dashboard. Details and resume selection are joined in one query, replacing per-job SQL queries.

## Workflow coverage

| Feature | Evidence and limits |
| --- | --- |
| Profile, preferences, date inputs | Schema tests, chronology checks, stale-save protection, browser profile editing. Profile truth is supplied by the user. |
| Multiple resumes | PDF/DOCX/TXT parsing, size checks, duplicate upload handling, local keyword corpus and recommendations. Scanned PDFs require OCR. Uploads are not automatically converted to verified XYZ achievements. |
| Discovery and manual links | Fixture parser tests and bounded live public requests. The sources below were tested; none promises exhaustive coverage. |
| Matching and priority | Coverage, seniority, missing skills, preferences, languages, source attribution, sponsorship and timestamp tests. Unknown eligibility still needs review. |
| ATS resume | Immutable full prompts, source evidence, XYZ metrics, 400–750 words, fixed reference format and one-page PDF tests. Sparse profiles correctly block export. |
| Cover letter and referrals | Word/character caps, exact source facts, job ID, public URL, low-pressure closing, editing and export checks. Contact recommendations are search leads, not verified employees or hiring managers. |
| Application answers | Verified stories, evidence selection, length limits and missing-input behavior. Drafts require review before use. |
| Interview coach | Role question generation and answer feedback. Rubric scores are practice feedback, not an interview outcome forecast. |
| Local models | Routing, cache, bounded analysis, source-validation tests. Existing three-case model trials are a small benchmark, not proof of general writing quality. |
| Opportunities | Delete/restore, persistence after rediscovery, queue protection, stable sorting and pagination. Deletion is reversible and retains documents. |
| Browser autofill and submission | Synthetic browser form tests and interruption/reservation regressions. No real employer application or LinkedIn message was sent during this review. |
| Privacy and dependencies | Source-only tracked-file scan, synthetic PDF template inspection and current Python/frontend advisory audits. No finite review can guarantee absence of vulnerabilities. |

## Public source checks

Public requests were made without cookies or account credentials. Results can change by region, time, filters, employer board and site policy. A successful HTTP response alone is not counted as extraction success.

| Source | Observed result |
| --- | --- |
| Remote OK | Public JSON feed returned successfully. |
| We Work Remotely | Public RSS feed returned successfully. |
| Remotive | Public API returned successfully; six-hour feed cache retained. |
| LinkedIn | Guest search returned public cards. Detail retrieval remains subject to access limits. |
| Arbeitnow Europe / UK | Both public APIs returned successfully. |
| Greenhouse | Airbnb example board returned jobs. A company slug is required. |
| Lever | Public example board returned an empty list, not an access error. Other employer boards must be selected explicitly. |
| Ashby | Ashby example board returned jobs. A company slug is required. |
| SmartRecruiters | Example company API returned postings. A company identifier is required. |
| Built In | Full JobPosting records extracted, including a Data Analyst keyword search. |
| Wellfound | Full public JobPosting records extracted from the featured-jobs snapshot. |
| Y Combinator / Work at a Startup | Work at a Startup returned HTTP 406. YC's public jobs site returned full postings and is used as the source. |
| Workable | Keyword search and individual postings returned full JobPosting records. A blank homepage does not list jobs. |
| Hacker News | Official jobstories/item APIs worked. Many posts have no full description; they remain limited-evidence leads. |
| AIJobs.net | Redirects to Foorilla; no readable job records were exposed on the landing page tested. |
| Indeed / Glassdoor | HTTP 403; removed from automatic search. Manual import remains available. |
| StepStone / HiringCafe | HTTP 403; removed from automatic search. |
| Google Jobs | Search page returned HTTP 200 but no structured JobPosting data. Manual import of the original employer posting remains necessary. |
| Berlin Startup Jobs | Three full public JobPosting records extracted, with dates and source attribution. |
| EU-Startups | Current board is `/startup-jobs/`. Three full JobPosting records extracted. Source-supplied employer facts are retained; the app does not verify advertiser identities. |
| Relocate.me | Three full JobPosting records extracted from `/international-jobs`. Some postings are older; their actual dates are preserved. Paid curated-list advertisements are excluded. |
| JobFluent | Three full public microdata postings extracted from the remote-job snapshot. Login-limited descriptions remain marked incomplete. |
| Working Nomads | Its linked public API worked; 50 records in the observed feed. Feed cached for six hours. |
| HV Capital / Earlybird / Point Nine | Three full public JobPosting records extracted from each board. Only observed public job-detail links are followed; external employer links are not blindly crawled. |
| Startup.jobs Germany | HTTP 403; excluded from automatic search. |
| GermanTechJobs | Redirected to JobCopilot signup from this installation. Search-engine text differed from direct access, so it is manual only. |
| Otta | Now Welcome to the Jungle. The jobs route redirected to login; manual only. |
| Index Ventures | `/careers/` returned 404. Current `/startup-jobs/` uses JavaScript search without embedded public postings; manual only. |
| Hyrise | Talent-community recruitment site. No public listing feed found; manual only. |

The directory contains 34 entries; the automatic picker includes 23 (19 public sources plus four employer boards). Greenhouse, Lever, Ashby and SmartRecruiters require an employer identifier. Known blocked sources and sites without readable listings remain in the manual directory. New HTTP 401/403/429/999 responses pause the entire source for one hour, remove it from the active picker and prevent immediate retries under different keywords. Saved opportunities are retained.

Requests use four source workers and at most two detail workers per public-page adapter, with bounded response sizes, host-checked redirects and caches. Public detail links are prioritized by keyword relevance before the ten-page limit. Search pages/feeds still need checking for new jobs; previously saved detail pages are reused. This does not enumerate every posting on a website.

### Access blocks

An AI model parses the content a site makes available; it does not grant access. Prefer official feeds/APIs, employer Greenhouse/Lever/Ashby/SmartRecruiters boards, or an authorized data partnership. For rate limits, honor cooldowns. For browser-only sources, use a normal browser session and manually import the posting. Rotating proxies, CAPTCHA solvers and copied account cookies were not added. A source may be accessible in a browser and still refuse the app's unauthenticated requests.


## Subscription and cloud models

This audit uses Codex. ChatGPT subscription access to Codex is separate from OpenAI Platform API billing; the app does not read Codex credentials or repurpose a ChatGPT login as an API key. See [official authentication documentation](https://learn.chatgpt.com/docs/auth).

OpenRouter offers free model variants. Its published free-account allowance is 50 requests/day across free models, rising to 1,000/day after buying at least $10 in credits; free capacity is limited and unsuitable as an assumed production guarantee. Its September 2026 [free-model list](https://openrouter.ai/collections/free-models) includes Nemotron 3 Ultra and Nemotron 3.5 Lightning, which are reasonable candidates for a controlled benchmark. Larger hosted models may improve extraction or drafting; they cannot guarantee access to blocked job sites. Use a pinned model for repeatable tests rather than a random free router.

See [OpenRouter limits](https://openrouter.ai/docs/faq) and [data-collection policy](https://openrouter.ai/docs/guides/privacy/data-collection). Provider policies differ, and some free variants permit training on submitted content. Start with synthetic profiles and public job descriptions. No OpenRouter integration, credentials, paid calls or cloud processing of candidate profiles were enabled in this review.

## Release verification

- 96 Python tests passed, including the three opt-in Chromium tests (full profile/upload/preparation/Studio/coaching journey, dashboard pagination, and local application form).
- Six Node tests passed for sorting and extension requisition identity.
- Production Next.js build and TypeScript checks passed.
- Python installed-environment audit and frontend production-dependency audit reported no known advisories at review time.
- Tracked and proposed source files were scanned for common credential patterns and personal paths/contact details; no matches were found. Local `.env`, profiles, databases, documents, caches, models and runtime logs remain ignored.
- The canonical resume PDF contains a synthetic candidate and one page.
- Local services were restarted successfully after a private SQLite backup. The saved profile fingerprint was unchanged.
- Docker Compose configuration validated; Docker runtime was not retested because its engine was stopped.

The local browser check displayed the saved dashboard, current source picker and running local model. These checks do not guarantee every employer form or future job-board response will work. All automated application submissions in tests used synthetic local forms.
