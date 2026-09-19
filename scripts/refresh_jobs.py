"""Six-hour hosted refresh for the small private beta.

The workflow uses the restricted backend role and applies the same RLS user
claim as an API request. Public job payloads/cache are shared; matches remain
private. No browser automation, credentials, or access-block bypass is used.
"""
import os

from sqlalchemy import text

from backend import database as db
from backend.agents.job_sources import discover
from backend.agents.orchestrator import discovery_graph

DEFAULT_SOURCES = "arbeitnow,arbeitnow_uk,remoteok,wwr,remotive,hackernews,workingnomads,jobbatical"


def users():
    with db.engine.connect() as conn:
        return [str(row[0]) for row in conn.execute(text("SELECT user_id FROM public.user_profiles WHERE full_name <> ''"))]


def main():
    if not db.HOSTED:
        raise SystemExit("DATABASE_URL is required for the hosted refresh")
    sources = [x.strip() for x in os.getenv("REFRESH_SOURCES", DEFAULT_SOURCES).split(",") if x.strip()]
    ceiling = int(os.getenv("MAX_JOBS_PER_REFRESH", "500"))
    total = 0
    for user_id in users():
        tokens = db.set_request_identity(user_id)
        try:
            profile, config = db.profile(), db.config()
            if not profile or not config:
                continue
            titles = config["job_search_criteria"].get("target_job_titles") or [""]
            keyword = titles[0] if titles else ""
            for source in sources:
                if total >= ceiling:
                    return
                try:
                    jobs, _cached = discover(source, keywords=keyword, limit=min(50, ceiling-total))
                    result = discovery_graph.invoke({"jobs": jobs, "profile": profile, "criteria": config["job_search_criteria"], "skip_seen": True})
                    total += result["count"]
                except Exception as exc:
                    print(f"{source}: {type(exc).__name__}")
        finally:
            db.reset_request_identity(tokens)
    print(f"Added {total} private matches")


if __name__ == "__main__":
    main()
