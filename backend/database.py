"""Persistence with local SQLite and RLS-protected hosted Postgres modes."""
import contextvars
import hashlib
import json
import os
import re
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event, text

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("DATA_DIR", str(ROOT / "data")))
DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
if os.name == "posix":
    DATA.chmod(0o700)

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
HOSTED = bool(DATABASE_URL)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL.removeprefix("postgres://")
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL.removeprefix("postgresql://")

engine = create_engine(
    DATABASE_URL or f"sqlite:///{DATA / 'career.db'}",
    pool_pre_ping=HOSTED,
    connect_args={"prepare_threshold": None} if HOSTED else {"check_same_thread": False},
)

if not HOSTED:
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

_user_id = contextvars.ContextVar("job_hunter_user_id", default="local" if not HOSTED else None)
_access_token = contextvars.ContextVar("job_hunter_access_token", default=None)


def set_request_identity(user_id: str, access_token: str | None = None):
    return _user_id.set(user_id), _access_token.set(access_token)


def reset_request_identity(tokens):
    _user_id.reset(tokens[0])
    _access_token.reset(tokens[1])


def current_user(required: bool = True) -> str:
    value = _user_id.get()
    if required and not value:
        raise RuntimeError("Authenticated user context is missing")
    return value or ""


def current_access_token() -> str | None:
    return _access_token.get()


def user_data_path(*parts) -> Path:
    root = DATA / "users" / current_user() if HOSTED else DATA
    return root.joinpath(*parts)


def _tenant_transaction(conn):
    if HOSTED:
        uid = current_user()
        claims = json.dumps({"sub": uid, "role": "authenticated"})
        conn.execute(text("SELECT set_config('request.jwt.claims', :claims, true)"), {"claims": claims})
        conn.execute(text("SET LOCAL ROLE job_hunter_backend"))


@contextmanager
def transaction():
    with engine.begin() as conn:
        _tenant_transaction(conn)
        yield conn


def init_db():
    if HOSTED:
        with transaction() as conn:
            conn.execute(text("SELECT 1"))
        return
    with engine.begin() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")
        for statement in (ROOT / "schema.sql").read_text().split(";"):
            if statement.strip():
                conn.exec_driver_sql(statement)
        conn.exec_driver_sql("CREATE TABLE IF NOT EXISTS job_details (job_id TEXT PRIMARY KEY, payload TEXT NOT NULL)")


def _postgres_sql(sql: str) -> str:
    if not HOSTED:
        return sql
    value = re.sub(r"\bdate\('now'\)", "CURRENT_DATE", sql, flags=re.I)
    had_ignore = bool(re.search(r"\bINSERT\s+OR\s+IGNORE\s+INTO\b", value, flags=re.I))
    value = re.sub(r"\bINSERT\s+OR\s+IGNORE\s+INTO\b", "INSERT INTO", value, flags=re.I)
    if had_ignore and "ON CONFLICT" not in value.upper():
        value += " ON CONFLICT DO NOTHING"
    return value.replace(",rowid DESC", ",kit_id DESC").replace("rowid DESC", "kit_id DESC").replace("archived=0", "archived=false")


def query(sql, params=None):
    with transaction() as conn:
        return [dict(row) for row in conn.execute(text(_postgres_sql(sql)), params or {}).mappings()]


def execute(sql, params=None):
    with transaction() as conn:
        conn.execute(text(_postgres_sql(sql)), params or {})


def _json(value):
    return value if isinstance(value, (dict, list)) else json.loads(value)


def profile(user_id=None):
    user_id = current_user() if user_id is None or HOSTED else user_id
    rows = query("SELECT * FROM user_profiles WHERE user_id=:id", {"id": user_id})
    if not rows:
        return None
    r = rows[0]
    return {
        "user_id": r["user_id"],
        "personal_details": {k: r[k] for k in ["full_name", "email", "phone", "location", "linkedin_url", "github_url", "portfolio_url", "work_authorization"]},
        "base_resume": _json(r["base_resume_json"]),
        "eeo_demographics": _json(r["eeo_demographics_json"]) if r["eeo_demographics_json"] else None,
    }


def config(user_id=None):
    user_id = current_user() if user_id is None or HOSTED else user_id
    rows = query("SELECT * FROM system_config WHERE user_id=:id", {"id": user_id})
    if not rows:
        return None
    r = rows[0]
    return {k: _json(r[v]) for k, v in [("job_search_criteria", "search_criteria_json"), ("execution_preferences", "execution_preferences_json"), ("llm_provider_config", "llm_config_json")]}


def profile_revision(value):
    # PostgreSQL drivers return UUID values as ``uuid.UUID`` objects.  They
    # are valid profile identifiers but are not JSON-native, so normalise
    # them before deriving the optimistic-concurrency revision.
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def applications(include_deleted=False, _job_id=None):
    where = []
    if not include_deleted:
        where.append("a.job_id NOT IN (SELECT job_id FROM deleted_opportunities)")
    if _job_id is not None:
        where.append("a.job_id=:id")
    rows = query(
        "SELECT a.*,d.payload,s.resume_id AS selected_resume_id,r.label AS selected_resume_label,sr.state AS studio_state,sr.error AS studio_error, "
        "(SELECT sk.kit_id FROM studio_kits sk WHERE sk.job_id=a.job_id ORDER BY sk.created_at DESC,sk.kit_id DESC LIMIT 1) AS studio_kit_id "
        "FROM application_records a LEFT JOIN job_details d ON d.job_id=a.job_id "
        "LEFT JOIN application_resume_selection s ON s.job_id=a.job_id "
        "LEFT JOIN resumes r ON r.resume_id=s.resume_id LEFT JOIN studio_runs sr ON sr.job_id=a.job_id "
        + (("WHERE " + " AND ".join(where)) if where else "")
        + " ORDER BY a.match_score DESC",
        {"id": _job_id},
    )
    from backend.services.job_matching import assess
    current_profile = profile()
    current_config = config()
    from backend.ai.router import settings
    ai_settings = settings() if current_config else None
    for r in rows:
        r["submission_logs"] = _json(r.pop("submission_logs_json"))
        r["extracted_form_fields"] = _json(r["extracted_form_fields"]) if r["extracted_form_fields"] else None
        payload = r.pop("payload")
        if payload:
            r.update(_json(payload))
        if r.get("selected_resume_id") == "profile":
            r["selected_resume_label"] = "Profile resume"
        if current_profile and current_config:
            r["fit_analysis"] = assess(r, current_profile, current_config["job_search_criteria"])
            r["match_score"] = r["fit_analysis"]["score"] / 100
            from backend.services.job_intelligence import enrich, ranking
            enriched = enrich(r, r)
            for key in ["source", "source_url", "posted_at", "posted_at_precision", "first_seen_at", "requisition_id", "visa_status", "visa_evidence", "visa_source", "visa_confidence", "visa_conflict", "visa_note", "language_requirements", "posting_language"]:
                r[key] = enriched[key]
            r["application_priority"] = ranking(r, current_profile, r["fit_analysis"]["score"], ai_settings)
    return sorted(rows, key=lambda r: r["match_score"], reverse=True)


def get_job(job_id):
    rows = applications(_job_id=job_id)
    return rows[0] if rows else None
