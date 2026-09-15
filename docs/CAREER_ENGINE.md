# Career engine

Job Hunter creates draft application material from the candidate's own evidence and a separate job description. Local models select or extract source evidence; application code renders and validates the result. Models cannot add free-form candidate claims to exported documents.

## Use it

1. Open **My profile** and enter your actual contact details, career dates, education and skills. Upload resume variants under Resumes for comparison and reference.
2. Open **Application Studio → Candidate evidence**. Write a factual 50–70-word profile summary. For each role, add XYZ achievements: outcome, actual measurement, and the method used. Check the confirmation box only for accurate facts. Save.
3. Add languages and verified stories for application questions. A story should describe the situation, your task, your own actions and the actual result. Use competency tags such as `stakeholder_management`, `negotiation`, `process_improvement`, or `problem_solving`.
4. Select a saved opening, read a supported public posting link, or paste the title, company and full job description. Review any extracted facts. Supply the employer's requisition number and a public resume/portfolio URL for referral messages. A local download link is not public; Job Hunter does not publish your resume.
5. Create a kit. Every asset displays its word/character count and missing evidence. Valid assets have download links. Invalid or incomplete assets remain reviewable previews and cannot be exported.
6. Paste application questions, one per line, and enter the form's actual limits. Different verified stories are preferred within a batch. Too-short evidence or answers exceeding a limit request input instead of inventing detail or silently clipping the answer.

Pasted raw candidate text can be extracted locally into a reviewable profile proposal. Fields must match exact source spans; dates or required identity fields that cannot be extracted faithfully require manual entry. Proposals do not overwrite your saved profile. Review every field before saving. Scanned resumes require OCR before upload.

The regular application-preparation flow uses these same validators and the same PDF renderer. Existing uploaded PDFs are not silently reused as compliant exports. Confirm the selected upload's facts in My profile and select **Profile resume** for generation. Uploaded originals remain downloadable. Legacy Studio kits must be regenerated to meet the new rules.

## Rules and precedence

The six instruction documents in `assets/` load in full into an immutable prompt registry. SHA-256 versions accompany generated assets and cache keys. Relevant full references are included for each task; profile/JD/template preferences are serialized separately as untrusted runtime data.

The instructions contain conflicting layout and length recommendations. This implementation prioritizes factual source evidence, then the task's explicit length/structure limits, then the fixed PDF's visual format. The source-controlled `assets/Resume template.pdf` is a sanitized synthetic reference; the original personal PDF with an underscore in its name is ignored. Personal example names in the format guide were replaced with generic examples; technical instructions were retained. The PDF layout is implemented in `backend/templates/career_resume.typ`, rather than editing or copying the original person's PDF.

- Resume: 400–750 whitespace-delimited words, 50–70-word summary, standard Markdown headings and `*` bullets, no tables/HTML/decorative symbols. Experience bullets use an action/outcome, an actual numeric measurement and a method. Exact source clauses or explicitly confirmed structured achievements are required. The most recent role can contain up to five bullets; older roles up to three. Each included role needs at least one valid achievement; sparse evidence blocks export.
- PDF: fixed one-page A4 serif layout, black text, centered identity, sections with rules, dates aligned to the right. Font sizes are tested at 10.5, 10 and 9.5 points. If content still overflows, export fails. Sections follow the reference PDF: Profile, Work Experience, Education, Skills, Languages, Certifications. Empty optional sections are omitted. Custom preferences cannot switch the required template.
- Cover letter: 250–400 words including header/sign-off; four body paragraphs for hook, source-backed impact, company/JD fit and CTA. One-page PDF with one-inch margins. Company context is quoted from the JD, not converted into candidate experience.
- LinkedIn: 75–125 words for post-connection/mutual-context messages; fewer than 300 characters for invitations. Exact title, requisition ID, an evidenced skill and public resume/portfolio URL are required. Missing values appear as placeholders but block export. Long titles/URLs can make an invite impossible within the cap; the app asks for input instead of dropping required fields. Shared-group context must be supplied by the user. Messages are not sent automatically.
- Application answers: verified source stories or selected experience facts; default 100–150 words for behavioural stories and 80–150 otherwise. Explicit smaller form limits take precedence. Drafts needing more facts remain non-exportable. The `autonomous` parameter checks limits only; it does not authorize form submission.

The guards prove traceability to supplied text, not the truth of a user's claims. They do not independently verify employment or validate the semantic relationship between every source clause. User-edited text is labelled for factual review and has structure/length checks repeated. Human review remains necessary before use.

## Matching, eligibility and freshness

Each opening shows the original source, source posting date/time when supplied, timestamp precision, first-seen time and explicit sponsorship evidence. Missing publication dates stay unknown; first seen is never represented as the posting date. Date-only/naive source timestamps do not imply an exact posting time. Sponsored advertising is not immigration sponsorship. Contradictory sponsorship statements remain unknown and require review; a positive quote is not a promise that the candidate qualifies.

Required and preferred languages are separated. Missing candidate proficiency means review; explicitly insufficient proficiency blocks an apply recommendation. The deterministic priority combines profile fit (80%), freshness (15%) and source quality (5%). Source and posting information is advisory and may be stale. Exact duplicate descriptions at the same company/title/location are combined, preferring direct ATS sources; alternate source links are retained.

Open a job and choose **Analyze this opening** for a bounded local model review. The staged report preserves raw facts and exposes component scores, source quotes, model stages, cache hits and usage. It does not silently replace the deterministic fit score. Near-duplicate embedding matches are flagged and skip repeat evaluation; they are not automatically merged on semantic similarity alone.

## Local model routing

`config/ai.json` defines task tiers, thresholds, scoring weights, context/output budgets and limits. **Local model lab → Task-specific model routing** saves per-installation choices. Models must already be installed; choose an embedding model for the embedding tier.

Example optional downloads, run in a terminal with Ollama installed:

```sh
ollama pull qwen2.5:1.5b
ollama pull qwen3:4b
ollama pull nomic-embed-text
```

Small handles extraction; medium handles evaluation and evidence selection; strong handles resume strategy and bounded deep job review. Medium and strong default to the existing configured reasoning model, so tiers can share a model. These defaults are not a claim that one model is best. Use the included synthetic benchmark and inspect generated evidence. That benchmark checks three extraction cases, not overall writing quality.

Analysis examines at most ten jobs per request and requests at most three deep reviews. A failed small-model response can retry and fall back to medium; other tiers do not automatically escalate to stronger models. Missing models, invalid JSON, timeouts or unsupported claims fall back to deterministic evidence or a missing-input result. Embedding analysis is optional and does not run without an installed embedding model.

Caches include profile/job/prompt/model versions. `data/ai-cache`, `answer-cache`, and `job-analysis-cache` contain private derived data. Usage logs contain model/task/token/latency metadata, not prompts or output text. Everything remains inside the ignored local `data/` folder. Delete these cache folders to remove cached derived data; saved profiles, uploads and kits have their own local storage. Never distribute your `data/` directory or `.env` file.

## API and verification

- `GET /api/v1/career/rules`
- `POST /api/v1/career/profile-intake` — raw text → unsaved reviewed proposal
- `POST /api/v1/career/generate` — resume, cover letter, post-connection, invite or mutual-group asset
- `POST /api/v1/career/answers` — bounded question batch
- `GET/PUT /api/v1/career/model-routing`
- `POST /api/v1/career/analyze` and `GET /api/v1/career/analyze/{id}` — background analysis
- Studio kit routes provide validated PDF/Markdown/text downloads.

Run `.venv/bin/python -m pytest -q` and `npm --prefix frontend run build`. `RUN_BROWSER_TESTS=1 .venv/bin/python -m pytest -q` also exercises the local browser submission guard in an isolated test environment. Tests use synthetic data and a temporary database, never your saved profile. No cloud API credentials are required for this pipeline.

## StepStone Germany

StepStone is available as a discovery source and in the board directory. Searches use public German keyword/location pages, read embedded JobPosting data, and follow at most ten same-host public posting links when necessary. Original source links, posting timestamps and requisition identifiers are retained when supplied. StepStone posting URLs can also be entered in Application Studio; blocked pages require pasted text.

Direct requests from the development machine returned HTTP 403 on September 15, 2026. This integration does not guarantee live retrieval: the UI reports **Unavailable**, offers the StepStone browser search and a manual-import action, and does not bypass login, CAPTCHA or access controls. Parser behavior is covered by synthetic fixtures; successful live extraction could not be verified from this connection. The published StepStone employer API is for publishing/managing listings, not used here as a candidate search API.

See [the local DeepSeek/Nemotron model trial](MODEL_TRIALS.md) for measured compatibility results and reproduction steps. Neither new model outperformed the existing model on this small extraction benchmark; installing them does not change the selected model.
