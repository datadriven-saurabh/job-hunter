# Job Hunter project plan

## Goal and users

Job Hunter is a private, local-first career workspace for one job seeker per installation. It helps a person discover suitable openings, understand the evidence behind a match, prepare truthful application materials, and track opportunities. A small authenticated hosted beta is supported, but broader hosted rollout is not currently active.

## Current product requirements and business rules

- Let users create a profile or review an editable draft from uploaded resumes. Never silently replace saved facts.
- Discover public postings through bounded source adapters, deduplicate them, explain source failures, and rank opportunities against profile evidence. Keep profile fit distinct from resume text similarity.
- Move jobs through New, Reviewing, and application states. Preserve user review and tracking decisions across later searches.
- Generate versioned, editable application kits from verified facts. Require user review before external submission or messaging. Keep base drafting functional without a paid model.
- Keep local personal data under ignored `data/`; never commit credentials, resumes, generated personal documents, or databases. Hosted data uses authenticated, owner-scoped storage.
- Treat Context.dev as an optional, explicit source. Send only title or keywords and location through the backend wrapper; never send a resume or full profile. Cache requests for 15 minutes and mock live calls in tests.

## Architecture and decisions

- `frontend/` is a Next.js and TypeScript workspace; `backend/` is a FastAPI service with discovery agents, matching and generation services. Local persistence uses SQLite. The hosted edition uses Supabase Auth, Postgres row-level security and private storage.
- Discovery uses bounded background runs and per-source cooldowns. This keeps slow or blocked sources from making every search appear stuck; it is not a durable distributed queue.
- Local deterministic matching and generation remain available when optional AI providers fail or are disabled. Model output passes evidence and format checks because application claims must come from user-provided facts.
- Soft-deleted opportunities stay excluded from rediscovery and can be restored. Current deletion also removes derived kits and documents; restoration does not recreate them.
- Source-controlled release material must be safe for a fresh installation. Generated promotional assets are separate from a tester's private `data/` directory.

## Planned scope, not yet implemented

The reviewed feature spec and implementation plan cover preserving all archived opportunity statuses and assets, targeted retries for unfinished discovery sources with completed results preserved and cooldowns respected, and related status/feedback improvements. Hosted beta expansion and opt-in telemetry are deferred pending user research; local personal data should not be uploaded for analytics. See the existing product spec and implementation-plan conversation for unresolved details before building these features.

## References

Read `docs/PROJECT_CONTEXT.md`, `docs/CAREER_ENGINE.md`, `docs/PRIVACY.md`, and `docs/DEVELOPMENT.md` for detailed state, data, and release rules. Update this plan only when scope or architecture changes.
