"""Origin, body-size, authentication, and hosted free-tier boundaries."""
import hashlib
import os
import re
import time
from threading import Lock

import httpx
from starlette.responses import JSONResponse

from backend import database as db

LOCAL_ORIGINS = {
    "http://localhost:3000", "http://127.0.0.1:3000",
    "http://localhost:8000", "http://127.0.0.1:8000",
}
PUBLIC_PATHS = {"/health", "/auth-config"}
_token_cache = {}
_cache_lock = Lock()


def web_origins():
    configured = {
        value.strip().rstrip("/")
        for value in (os.getenv("APP_URL", "") + "," + os.getenv("ADDITIONAL_WEB_ORIGINS", "")).split(",")
        if value.strip()
    }
    return LOCAL_ORIGINS | configured


def extension_origins():
    if db.HOSTED:
        return set()
    return {
        "chrome-extension://" + value.strip()
        for value in os.getenv("TRUSTED_EXTENSION_IDS", "").split(",")
        if re.fullmatch("[a-p]{32}", value.strip())
    }


def _verify_supabase_token(token: str):
    digest = hashlib.sha256(token.encode()).hexdigest()
    now = time.time()
    with _cache_lock:
        cached = _token_cache.get(digest)
        if cached and cached[1] > now:
            return cached[0]
    url = os.environ["SUPABASE_URL"].rstrip("/") + "/auth/v1/user"
    try:
        response = httpx.get(
            url,
            headers={"apikey": os.environ["SUPABASE_ANON_KEY"], "Authorization": "Bearer " + token},
            timeout=8,
        )
        response.raise_for_status()
        user = response.json()
        user_id = user.get("id")
        if not isinstance(user_id, str) or not re.fullmatch(r"[0-9a-f-]{36}", user_id, re.I):
            raise ValueError("invalid user")
    except Exception:
        return None
    with _cache_lock:
        _token_cache[digest] = (user_id, now + 60)
        if len(_token_cache) > 500:
            for key, value in list(_token_cache.items()):
                if value[1] <= now:
                    _token_cache.pop(key, None)
    return user_id


def _rate_event(path: str, method: str):
    if method == "POST" and path in {"/api/v1/jobs/search", "/api/v1/jobs/search-runs"}:
        return "JOB_SEARCH", int(os.getenv("MAX_SEARCHES_PER_USER_PER_DAY", "10"))
    if method == "POST" and path == "/api/v1/resumes/upload":
        return "RESUME_PARSE", int(os.getenv("MAX_RESUME_PARSES_PER_USER_PER_DAY", "5"))
    if method == "POST" and (path.endswith("/answers") or path == "/api/v1/career/generate"):
        return "AI_GENERATION", int(os.getenv("MAX_AI_CALLS_PER_USER_PER_DAY", "30"))
    return None


def _consume_limit(path: str, method: str):
    value = _rate_event(path, method)
    if not value:
        return True
    event, limit = value
    user_id = db.current_user()
    count = db.query(
        "SELECT COUNT(*) AS n FROM usage_events WHERE user_id=:user_id AND event_type=:event AND created_at >= CURRENT_TIMESTAMP - INTERVAL '1 day'",
        {"user_id": user_id, "event": event},
    )[0]["n"]
    if count >= limit:
        return False
    db.execute("INSERT INTO usage_events(user_id,event_type) VALUES (:user_id,:event)", {"user_id": user_id, "event": event})
    return True


class LocalSecurityMiddleware:
    """Retained class name to avoid breaking imports in the local edition."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope["headers"])
        origin = headers.get(b"origin", b"").decode("latin1").rstrip("/")
        extensions = extension_origins()
        allowed = web_origins() | extensions
        if ((origin and origin not in allowed)
                or (not origin and headers.get(b"sec-fetch-site") == b"cross-site")):
            return await JSONResponse({"detail": "Untrusted origin"}, status_code=403)(scope, receive, send)

        if scope["method"] == "OPTIONS" and origin in extensions:
            return await JSONResponse({}, status_code=200, headers={
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Methods": "GET, POST, PATCH, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
                "Vary": "Origin",
            })(scope, receive, send)
        if scope["method"] == "OPTIONS":
            return await self.app(scope, receive, send)

        identity_tokens = None
        if db.HOSTED and scope["path"] not in PUBLIC_PATHS:
            authorization = headers.get(b"authorization", b"").decode("latin1")
            if not authorization.startswith("Bearer "):
                return await JSONResponse({"detail": "Authentication required"}, status_code=401)(scope, receive, send)
            access_token = authorization[7:].strip()
            user_id = _verify_supabase_token(access_token)
            if not user_id:
                return await JSONResponse({"detail": "Session expired or invalid"}, status_code=401)(scope, receive, send)
            identity_tokens = db.set_request_identity(user_id, access_token)
            try:
                if not _consume_limit(scope["path"], scope["method"]):
                    return await JSONResponse({"detail": "Daily free-tier limit reached. Try again tomorrow."}, status_code=429)(scope, receive, send)
            except Exception:
                db.reset_request_identity(identity_tokens)
                return await JSONResponse({"detail": "Could not verify usage limits"}, status_code=503)(scope, receive, send)

        limit = (11 if scope["path"] == "/api/v1/resumes/upload" else 1) * 1024 * 1024
        length = headers.get(b"content-length")
        if length is not None:
            try:
                size = int(length)
                if size < 0:
                    raise ValueError()
            except ValueError:
                if identity_tokens:
                    db.reset_request_identity(identity_tokens)
                return await JSONResponse({"detail": "Invalid content length"}, status_code=400)(scope, receive, send)
            if size > limit:
                if identity_tokens:
                    db.reset_request_identity(identity_tokens)
                return await JSONResponse({"detail": "Request body too large"}, status_code=413)(scope, receive, send)
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                if identity_tokens:
                    db.reset_request_identity(identity_tokens)
                return
            body.extend(message.get("body", b""))
            if len(body) > limit:
                if identity_tokens:
                    db.reset_request_identity(identity_tokens)
                return await JSONResponse({"detail": "Request body too large"}, status_code=413)(scope, receive, send)
            if not message.get("more_body", False):
                break

        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        async def secure_send(message):
            if message["type"] == "http.response.start":
                extra = [
                    (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"x-frame-options", b"DENY"),
                ]
                names = {name for name, _ in extra}
                message["headers"] = [(k, v) for k, v in message.get("headers", []) if k.lower() not in names] + extra
            await send(message)

        try:
            return await self.app(scope, replay, secure_send)
        finally:
            if identity_tokens:
                db.reset_request_identity(identity_tokens)
