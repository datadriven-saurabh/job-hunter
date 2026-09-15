# Job Hunter AI Optimization Plan

## Objective

Refactor the Job Hunter project so that different AI models are used for different stages of the pipeline.

The goals are:

- Improve matching accuracy
- Reduce unnecessary token/model usage
- Use cheaper models for high-volume deterministic tasks
- Reserve stronger reasoning models for ambiguous or high-value decisions
- Make scoring reproducible and explainable
- Reduce false positives for visa sponsorship and language eligibility
- Cache model outputs so repeated jobs are not reprocessed
- Make model selection configurable from one place

---

# 1. High-Level Architecture

Use a staged pipeline instead of sending every job directly to the strongest model.

```text
Job Sources
   ↓
Deterministic Extraction
   ↓
Normalization
   ↓
Deduplication
   ↓
Hard Filters
   ↓
Small Model Classification
   ↓
Embedding Similarity
   ↓
Medium Model Evaluation
   ↓
Strong Model Deep Evaluation
   ↓
Resume Tailoring / Outreach
   ↓
Final Ranked Jobs
```

The strongest model should only process a small percentage of all collected jobs.

Example target flow:

```text
1000 collected jobs
↓
450 after deterministic/hard filters
↓
250 after small-model classification
↓
75 after embeddings + heuristic scoring
↓
25 after medium-model evaluation
↓
10–20 after strong-model evaluation
```

---

# 2. Model Routing Strategy

Do not hard-code one model across the project.

Introduce model tiers:

```text
small
medium
strong
embedding
```

Suggested responsibilities:

| Stage | Task | Model Tier |
|---|---|---|
| Job scraping | Fetch pages/APIs | No LLM |
| HTML cleaning | Parse page content | No LLM |
| Basic normalization | Title/location cleanup | Rules |
| Duplicate detection | Hashes + embeddings | Embedding |
| Job extraction | Skills, years, languages | Small |
| Eligibility classification | Role/seniority/language | Small |
| Initial relevance | Candidate ↔ JD similarity | Embedding |
| Detailed job scoring | Skills/domain/seniority | Medium |
| Sponsorship ambiguity | Evidence-based review | Strong |
| Deep fit analysis | Top jobs only | Strong |
| Resume strategy | Determine what to tailor | Strong |
| Resume rewriting | Rewrite approved bullets | Medium |
| Cover letter | Generate concise tailored draft | Medium |
| Recruiter outreach | Draft outreach | Medium |
| Final shortlist ranking | Compare best jobs | Strong |

---

# 3. Central Model Configuration

Create a single model configuration rather than placing model names throughout the application.

Example:

```yaml
models:

  extraction:
    tier: small
    temperature: 0

  classification:
    tier: small
    temperature: 0

  scoring:
    tier: medium
    temperature: 0

  deep_analysis:
    tier: strong
    reasoning: medium

  sponsorship_review:
    tier: strong
    reasoning: medium

  resume_strategy:
    tier: strong
    reasoning: medium

  resume_writing:
    tier: medium
    temperature: 0.2

  outreach:
    tier: medium
    temperature: 0.3

  embeddings:
    tier: embedding
```

Application code should request a task type, not a model directly.

Example:

```python
model = model_router.get("job_extraction")
```

Do not write:

```python
model = "specific-model-name"
```

throughout the codebase.

---

# 4. Introduce a Model Router

Create a reusable model router.

Example interface:

```python
class ModelRouter:

    def get(self, task: str):
        ...

    def run(self, task: str, prompt: str, schema=None):
        ...
```

The router should support:

- Task → model mapping
- Retry logic
- Fallback models
- Token usage logging
- Latency logging
- Structured output validation
- Cost/usage tracking
- Model overrides for testing

Suggested fallback pattern:

```text
small model
↓
invalid output?
retry small once
↓
still invalid?
medium model
↓
low confidence or ambiguity?
strong model
```

Do not automatically jump from a small model failure to the most expensive model.

---

# 5. Remove LLM Usage Where Code Is Better

LLMs should not be used for deterministic tasks.

Use code/rules for:

- HTML cleanup
- URL normalization
- Dates
- Salary parsing where possible
- Known location mapping
- Country mapping
- Duplicate URL detection
- Exact duplicate descriptions
- Keyword-based rejection rules
- Application timestamps
- Job age
- Excluded countries
- Explicit required language rules
- Obvious seniority mismatch

Example:

```python
if job.country in EXCLUDED_COUNTRIES:
    reject(job)

if job.age_days > MAX_JOB_AGE_DAYS:
    reject(job)

if job.required_language in HARD_LANGUAGE_EXCLUSIONS:
    reject(job)

if job.role_family not in TARGET_ROLE_FAMILIES:
    reject(job)
```

Do this before any expensive model call.

---

# 6. Structured Job Extraction

Use a small model to convert a job description into strict structured data.

Do not request prose.

Suggested schema:

```python
class StructuredJob(BaseModel):
    role_family: str
    seniority: str | None
    years_required_min: int | None
    years_required_max: int | None

    required_skills: list[str]
    preferred_skills: list[str]

    required_languages: list[str]
    preferred_languages: list[str]

    country: str | None
    city: str | None
    remote_type: str | None

    visa_status: str
    relocation_status: str

    employment_type: str | None

    hard_requirements: list[str]
    preferred_requirements: list[str]

    confidence: float
```

Use JSON schema / Pydantic validation.

If the output is invalid:

1. Retry once with the same small model
2. Send validation error feedback
3. Escalate to medium only if required

---

# 7. Visa Sponsorship Must Be Evidence-Based

Visa sponsorship is a critical field and should not be inferred casually.

Use:

```python
VisaStatus = Literal[
    "explicit_yes",
    "explicit_no",
    "likely",
    "unknown"
]
```

Store evidence:

```python
{
    "visa_status": "explicit_yes",
    "visa_evidence": "We provide visa sponsorship and relocation support."
}
```

Rules:

### `explicit_yes`

Only use when the job description or official company source explicitly mentions:

- visa sponsorship
- work permit sponsorship
- immigration support
- relocation with visa support

### `explicit_no`

Use when the posting explicitly says:

- no sponsorship
- must already have work authorization
- sponsorship is unavailable
- EU/EEA-only eligibility where applicable

### `likely`

Use only when there is meaningful indirect evidence.

Do not present this to the user as confirmed sponsorship.

### `unknown`

Default to unknown whenever evidence is insufficient.

Important:

```text
"Sponsored job"
```

on a job board must NOT be interpreted as immigration sponsorship.

Store:

```python
visa_confidence: float
visa_evidence: str | None
visa_source: str | None
```

---

# 8. Language Eligibility

Do not let semantic matching override hard language requirements.

Store:

```python
required_languages
preferred_languages
```

Examples:

```text
German C1 required
French required
Dutch mandatory
```

should be handled as hard requirements.

If the user's proficiency does not satisfy the requirement:

```python
language_eligible = False
```

unless the requirement is explicitly preferred rather than mandatory.

---

# 9. Job Deduplication

Jobs frequently appear across multiple sources.

Add several levels of deduplication.

## Level 1: Exact URL

Normalize URLs and remove tracking parameters.

## Level 2: Exact content hash

```python
normalized = normalize_description(job.description)
job_hash = sha256(normalized.encode()).hexdigest()
```

## Level 3: Composite fingerprint

```text
company
+
normalized title
+
location
+
description hash
```

## Level 4: Embedding similarity

Use embeddings to detect near-duplicate descriptions.

When duplicates are found:

- Keep the official company / ATS source when available
- Store all alternative source URLs
- Do not re-run AI analysis

Preferred source priority:

```text
Official company careers page
>
Greenhouse / Lever / Workday / ATS
>
LinkedIn / Indeed
>
other aggregators
```

---

# 10. Embedding-Based Initial Ranking

Do not run full reasoning against every job.

Create a normalized candidate profile text containing:

- Target role families
- Relevant experience
- Core skills
- Industry/domain experience
- Tools
- Years of experience
- Geography preferences
- Language ability

Generate a candidate embedding once.

Generate one embedding for each normalized job.

Calculate cosine similarity.

Example:

```python
embedding_similarity = cosine_similarity(
    candidate_embedding,
    job_embedding,
)
```

Use this as an initial relevance feature, not the final decision.

---

# 11. Initial Scoring Should Be Mostly Deterministic

Calculate an initial score before calling the medium model.

Example:

```python
initial_score = (
    semantic_similarity * 0.30
    + skill_overlap * 0.25
    + experience_fit * 0.15
    + seniority_fit * 0.10
    + language_fit * 0.10
    + location_fit * 0.10
)
```

Weights should live in configuration.

Example:

```yaml
scoring:
  semantic_similarity: 0.30
  skill_overlap: 0.25
  experience_fit: 0.15
  seniority_fit: 0.10
  language_fit: 0.10
  location_fit: 0.10
```

Jobs below a configurable threshold should not reach the medium model.

Example:

```yaml
thresholds:
  minimum_initial_score: 0.55
```

---

# 12. Medium Model Evaluation

The medium model should only evaluate jobs that pass the first-stage filters.

Its output should be structured.

Example:

```python
class JobEvaluation(BaseModel):
    skills_score: int
    experience_score: int
    domain_score: int
    seniority_score: int
    language_score: int
    location_score: int

    strengths: list[str]
    gaps: list[str]
    hard_requirements_missing: list[str]

    recommendation: Literal[
        "reject",
        "low_priority",
        "apply",
        "high_priority"
    ]

    confidence: float
```

The model should NOT produce the final weighted score itself.

Code calculates:

```python
final_score = (
    skills_score * weights.skills
    + experience_score * weights.experience
    + domain_score * weights.domain
    + seniority_score * weights.seniority
    + language_score * weights.language
    + location_score * weights.location
)
```

This makes scoring more reproducible.

---

# 13. Strong Model Escalation

Only escalate a job to the strongest model when needed.

Example conditions:

```python
should_escalate = (
    evaluation.final_score >= HIGH_VALUE_THRESHOLD
    or evaluation.confidence < LOW_CONFIDENCE_THRESHOLD
    or visa_status in {"likely", "unknown"}
    or conflicting_requirements_detected
    or job_is_top_ranked
)
```

Suggested logic:

```python
if evaluation.final_score < 65 and evaluation.confidence >= 0.9:
    return evaluation

if evaluation.final_score >= 80:
    return strong_model_review(job)

if evaluation.confidence < 0.7:
    return strong_model_review(job)

if visa_status in {"likely", "unknown"} and evaluation.final_score >= 70:
    return strong_model_review(job)
```

The strong model should focus on:

- Ambiguous requirements
- Visa/relocation interpretation
- Career trajectory fit
- Domain transferability
- Hidden red flags
- Whether missing requirements are genuinely blocking
- Ranking among other shortlisted roles

---

# 14. Resume Tailoring Should Use Two Different Stages

Do not ask the writing model to decide what should change.

Separate strategy from rewriting.

## Stage A: Resume Strategy

Use strong model.

Input:

- Candidate resume
- Structured job
- Evaluation
- Existing bullet points

Output:

```json
{
  "priority_keywords": [],
  "experience_to_emphasize": [],
  "bullets_to_rewrite": [],
  "skills_to_surface": [],
  "do_not_claim": [],
  "red_flags": []
}
```

The strong model determines the strategy.

## Stage B: Resume Writing

Use medium model.

The medium model receives the approved strategy and rewrites only the selected sections.

Instruction:

```text
Do not invent new achievements.
Do not create metrics that are not present in the source resume.
Do not add skills that the candidate does not possess.
Preserve factual meaning.
Optimize for clarity and ATS keyword alignment.
```

This reduces both cost and hallucination risk.

---

# 15. Cover Letter and Recruiter Outreach

Use medium models for:

- Cover letters
- Recruiter messages
- Referral messages
- Application question drafting
- Follow-up messages

These tasks generally do not require the strongest reasoning model once job analysis has already been completed.

They should consume structured context from the previous stages instead of the full JD repeatedly.

Example:

```python
context = {
    "company": job.company,
    "role": job.title,
    "top_strengths": evaluation.strengths[:3],
    "relevant_experience": resume_strategy.experience_to_emphasize,
}
```

---

# 16. Cache Every Expensive Result

Introduce caching based on stable hashes.

Cache:

- Structured job extraction
- Embeddings
- Medium model evaluation
- Strong model review
- Resume strategy
- Job/company sponsorship evidence

Example cache key:

```python
cache_key = sha256(
    (
        job_hash
        + prompt_version
        + model_version
        + candidate_profile_version
    ).encode()
).hexdigest()
```

Do not reprocess jobs when the job description has not changed.

Invalidate cache when:

- Job content changes
- Candidate profile changes
- Prompt version changes
- Scoring logic changes

---

# 17. Prompt Versioning

Every production prompt should have a version.

Example:

```python
JOB_EXTRACTION_PROMPT_VERSION = "v3"
JOB_SCORING_PROMPT_VERSION = "v2"
VISA_REVIEW_PROMPT_VERSION = "v4"
```

Store the prompt version alongside the result.

Example database fields:

```text
model_name
model_tier
prompt_version
created_at
input_tokens
output_tokens
latency_ms
```

This makes debugging model behaviour much easier.

---

# 18. Separate Raw Facts from AI Analysis

Never overwrite source data with AI-generated values.

Recommended structure:

```text
jobs
├── id
├── source
├── source_url
├── company
├── raw_title
├── raw_description
├── raw_location
├── posted_at

structured_jobs
├── job_id
├── normalized_title
├── role_family
├── seniority
├── skills
├── languages
├── years_required
├── visa_status
├── visa_evidence
├── relocation_status

job_scores
├── job_id
├── semantic_score
├── skill_score
├── experience_score
├── language_score
├── final_score
├── scoring_version

job_analysis
├── job_id
├── strengths
├── gaps
├── red_flags
├── recommendation
├── model
├── prompt_version
```

---

# 19. Confidence-Aware Processing

Every AI classifier/evaluator should return confidence.

Example:

```python
confidence: float
```

Use confidence to decide whether to escalate.

Example:

```text
confidence >= 0.90
→ trust medium result if score is clearly low

confidence 0.70–0.90
→ normal processing

confidence < 0.70
→ escalate to stronger model
```

This is more efficient than simply escalating every high-score job.

---

# 20. Freshness Rules

Prioritize recently posted jobs.

Add fields:

```python
posted_at
first_seen_at
last_seen_at
```

Add configurable rules:

```yaml
job_freshness:
  preferred_days: 7
  maximum_days: 30
```

A recent official job should generally outrank an old aggregator listing.

Job freshness should contribute to application priority but not replace fit scoring.

---

# 21. Source Quality Score

Introduce a source-quality field.

Example:

```python
source_quality = {
    "official_company": 1.0,
    "ats": 0.95,
    "linkedin": 0.85,
    "indeed": 0.80,
    "aggregator": 0.60,
}
```

Use it in prioritization and duplicate resolution.

---

# 22. Suggested Final Ranking Formula

Final application priority should combine multiple signals.

Example:

```python
application_priority = (
    fit_score * 0.55
    + visa_score * 0.15
    + freshness_score * 0.10
    + source_quality * 0.05
    + career_value_score * 0.10
    + relocation_score * 0.05
)
```

Keep all weights configurable.

Do not allow an LLM to invent the final ranking score directly.

---

# 23. Recommended Candidate Decision States

Use explicit states:

```python
REJECTED
LOW_PRIORITY
REVIEW
APPLY
HIGH_PRIORITY
APPLIED
INTERVIEW
OFFER
CLOSED
```

Example rules:

```text
Hard eligibility failure
→ REJECTED

Fit < threshold
→ LOW_PRIORITY

Ambiguous sponsorship / requirements
→ REVIEW

Strong match
→ APPLY

Strong match + confirmed sponsorship + recent posting
→ HIGH_PRIORITY
```

---

# 24. Observability

Log AI usage by task.

Track:

```text
task_type
model
model_tier
job_id
input_tokens
output_tokens
latency
retry_count
fallback_used
cache_hit
confidence
```

Build basic aggregate metrics:

```text
Total jobs processed
LLM calls per job
Strong-model calls per 100 jobs
Average cost per discovered job
Average cost per shortlisted job
Cache hit rate
Extraction failure rate
Escalation rate
```

The goal should be to minimize:

```text
strong-model calls / total jobs
```

without reducing shortlist quality.

---

# 25. Evaluation Dataset

Create a manually reviewed evaluation dataset.

Example:

```text
evals/jobs.jsonl
```

Each entry should contain:

```json
{
  "job_description": "...",
  "expected_role_family": "data_analyst",
  "expected_language_eligible": true,
  "expected_visa_status": "unknown",
  "expected_decision": "apply"
}
```

Include challenging examples:

- Explicit sponsorship
- Explicit no sponsorship
- Ambiguous relocation wording
- German-required jobs
- German-preferred jobs
- Senior jobs outside candidate experience
- Closely related BI/Data Analyst jobs
- Unrelated engineering jobs
- Duplicate jobs from different sources

Run evaluation before changing model assignments or prompts.

---

# 26. Tests to Add

## Unit Tests

Add tests for:

- Hard filtering
- Language filtering
- Visa status mapping
- Score calculation
- Model router
- Cache keys
- Duplicate detection
- Source prioritization
- Freshness scoring

## Structured Output Tests

Verify:

- Invalid JSON triggers retry
- Missing mandatory fields trigger retry
- Low confidence triggers escalation
- Strong model is not called unnecessarily

## Integration Tests

Example:

```text
Job ingestion
→ extraction
→ eligibility
→ embeddings
→ scoring
→ escalation
→ final recommendation
```

---

# 27. Suggested Module Structure

A possible organization:

```text
job_hunter/
├── config/
│   ├── models.yaml
│   ├── scoring.yaml
│   └── filters.yaml
│
├── ai/
│   ├── model_router.py
│   ├── schemas.py
│   ├── prompts/
│   │   ├── extraction.py
│   │   ├── evaluation.py
│   │   ├── visa_review.py
│   │   ├── resume_strategy.py
│   │   └── resume_writer.py
│   └── cache.py
│
├── jobs/
│   ├── normalize.py
│   ├── deduplicate.py
│   ├── eligibility.py
│   ├── embeddings.py
│   ├── scoring.py
│   └── ranking.py
│
├── resume/
│   ├── strategy.py
│   ├── tailoring.py
│   └── validation.py
│
├── outreach/
│   ├── cover_letter.py
│   └── recruiter_message.py
│
├── evals/
│   ├── jobs.jsonl
│   └── run_evals.py
│
└── tests/
```

Adapt this structure to the existing project rather than rewriting the project unnecessarily.

---

# 28. Migration Strategy

Do not rewrite the full system in one change.

Implement in phases.

## Phase 1

Introduce:

- Model router
- Central model configuration
- Usage logging

Do not change scoring behaviour yet.

## Phase 2

Move bulk extraction/classification to small model.

Add structured output validation.

## Phase 3

Add embeddings and initial deterministic ranking.

Reduce medium/strong model calls.

## Phase 4

Introduce strong-model escalation based on:

- high job value
- ambiguity
- low confidence

## Phase 5

Split resume strategy from resume writing.

## Phase 6

Add caching and prompt versioning.

## Phase 7

Add evaluation suite and tune thresholds.

---

# 29. Coding-Agent Instructions

When implementing this optimization:

1. Inspect the current project first.
2. Reuse the existing architecture wherever reasonable.
3. Do not rewrite unrelated modules.
4. Do not replace working integrations unless necessary.
5. Introduce model routing incrementally.
6. Keep model names configurable.
7. Keep scoring weights configurable.
8. Preserve raw job data separately from model-derived data.
9. Add tests for each routing decision.
10. Avoid speculative abstractions.
11. Do not make the strongest model the default fallback for every failure.
12. Prefer strict structured model outputs over free-form prose.
13. Ensure visa sponsorship remains evidence-based.
14. Ensure hard language requirements cannot be overridden by semantic similarity.
15. Cache previously processed jobs.
16. Report before/after model call counts where possible.

---

# 30. Acceptance Criteria

The optimization is complete when:

- [ ] The project has a central model router
- [ ] Model assignments are configurable
- [ ] Small models handle bulk extraction/classification
- [ ] Embeddings are used for first-pass similarity
- [ ] Medium models only process shortlisted jobs
- [ ] Strong models only process high-value or ambiguous cases
- [ ] Visa sponsorship is evidence-based
- [ ] Hard language filters are implemented
- [ ] Job deduplication prevents repeated LLM processing
- [ ] AI responses use validated structured schemas
- [ ] All expensive outputs are cached
- [ ] Prompt/model versions are stored
- [ ] Resume analysis and resume rewriting use separate model stages
- [ ] Final scores are calculated by code rather than invented by an LLM
- [ ] Token/model usage is logged
- [ ] Evaluation tests exist
- [ ] Existing functionality continues to work

---

# 31. Desired Outcome

The final system should behave like this:

```text
Most jobs:
No LLM or small model only

Potentially relevant jobs:
Small model + embeddings

Strong candidates:
Medium model

Best or ambiguous candidates:
Strong model

Resume strategy for top applications:
Strong model

Resume rewriting / cover letter / outreach:
Medium model
```

The design should optimize for:

```text
High recall early
+
high precision late
+
minimal use of expensive reasoning models
```

Do not optimize purely for lowest cost. The goal is to spend model capacity where it has the highest effect on application quality.
