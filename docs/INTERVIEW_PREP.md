# Interview preparation and question repository

The repository lives in `backend/content/interview/questions.json`: 68 original practice questions, stable IDs, eight specialist role families plus General, stages, categories, rubrics, answer guidance and follow-ups. It ships with the app and needs no paid service, model call or runtime crawling. This is a content repository within Job Hunter, not a separate GitHub repository.

The coach supports all-question browsing without a saved job, role/category/stage/text filters, role-matched practice, previous/next navigation, and per-question answer drafts and feedback held in React memory. Leaving the view or refreshing clears drafts. Feedback requests send the selected answer to the backend; this feature does not persist answers. Existing optional loopback-model feedback remains supported. Otherwise scoring measures keyword coverage only, not technical correctness, factual accuracy, or hiring likelihood. Missing rubric elements are shown explicitly.

Matching uses boundary-aware role title terms, then topic mentions in the job title/description to rank relevant questions. A behavioral warmup comes first. Unknown roles receive general questions; software design is not assigned to every job. Matching is a preparation heuristic, not a probability of being asked. Stable bank IDs replace process-local generated-question caches, allowing feedback after server restarts.

## Sources reviewed on 24 September 2026

- [LinkedIn interviewing guide](https://business.linkedin.com/hire/resources/interviewing-talent/interview-questions-for-candidates): general behavioral assessment and structured examples.
- [Glassdoor question types](https://www.glassdoor.com/blog/guide/types-of-interview-questions/): recruiter, skills, situational and closing categories.
- [Reddit SQL interview discussion](https://www.reddit.com/r/SQL/comments/1d8q9x1/here_are_the_most_common_data_analystscience_sql/): anecdotal topic context, not verified company questions.
- [AmbitionBox data analyst interviews](https://www.ambitionbox.com/profiles/data-analyst/interview-questions?page=1): search-index discovery only; full-page access failed. Retained visibly as a research link, never as evidence for a question.

Prompts and coaching guidance are original editorial exercises. Source links indicate thematic context, not verbatim extraction, employer attribution, frequency, or an exhaustive collection. Unsourced technical scenarios are explicitly original. No private feeds, sign-in bypasses, or automated scraping were used.

## Maintenance

Add entries with unique stable IDs; never reuse an existing ID for a different question. Supply role families, topic tags, stage, difficulty, a nonempty rubric, question-specific guidance, follow-ups, provenance and review date. Add a source only if reviewed and relevant; distinguish reported experiences from verified employer materials. Do not copy proprietary question banks, answers, private identities or resume information. The catalog is loaded once per process; restart after content changes.

Endpoints: `GET /api/v1/interview/catalog`, `GET /api/v1/interview/questions` (optional job_id, role_family, category, stage, query), existing `POST /api/v1/interview/generate-questions`, and `POST /api/v1/interview/evaluate` (job_id optional). Job access still goes through the owner-scoped lookup. General bank content is shared and contains no user data.

Run `PYTHONPATH=. .venv/bin/pytest tests/test_interview_bank.py tests/test_workflow.py -q`, frontend typecheck/build, and the opt-in interview browser test. No production deployment is implied by local checks.
