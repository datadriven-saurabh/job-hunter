# Project guidance for coding agents

## Context.dev job discovery

- The optional Context.dev source is `contextdev` in `backend/agents/job_sources.py`. It is available only when `CONTEXT_DEV_API_KEY` is configured server-side. Put the key in ignored `.env` for local runs or a server secret manager for hosted runs. Never commit, log, or send the key to the frontend.
- Route every Context.dev request through `backend/services/context_dev.py`. The wrapper uses the official Python SDK and only `POST /web/search` for this source. Search receives the user's job title or keywords and location, never their resume or full profile. The existing local discovery graph applies profile criteria to returned candidates.
- One request asks for 10 results and Markdown from direct ATS domains, costing up to 2 credits. Results are cached by the project for 15 minutes; the UI lists Context.dev in its own category so searches are explicit. No automated test may call the live API; mock `search_web`.
- Documentation: [agent quickstart](https://docs.context.dev/agent-quickstart), [Python SDK](https://docs.context.dev/sdks/python), [web search endpoint](https://docs.context.dev/api-reference/web-scraping/search), [credits](https://docs.context.dev/account/credits), [troubleshooting](https://docs.context.dev/optimization/troubleshooting).
