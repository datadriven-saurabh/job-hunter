"""Private Supabase Storage access using the verified user's token."""
import mimetypes
import os
from urllib.parse import quote

import httpx

from backend import database as db


def enabled():
    return db.HOSTED


def uri(bucket: str, key: str):
    return f"supabase://{bucket}/{key}"


def parse(value: str):
    if not value.startswith("supabase://"):
        return None
    bucket, key = value.removeprefix("supabase://").split("/", 1)
    return bucket, key


def _headers(content_type=None):
    headers = {
        "apikey": os.environ["SUPABASE_ANON_KEY"],
        "Authorization": "Bearer " + (db.current_access_token() or ""),
    }
    if content_type:
        headers.update({"Content-Type": content_type, "x-upsert": "true"})
    return headers


def put(bucket: str, key: str, content: bytes, content_type: str | None = None):
    content_type = content_type or mimetypes.guess_type(key)[0] or "application/octet-stream"
    url = os.environ["SUPABASE_URL"].rstrip("/") + f"/storage/v1/object/{bucket}/{quote(key, safe='/')}"
    response = httpx.post(url, headers=_headers(content_type), content=content, timeout=30)
    response.raise_for_status()
    return uri(bucket, key)


def get(value: str):
    location = parse(value)
    if not location:
        return None
    bucket, key = location
    url = os.environ["SUPABASE_URL"].rstrip("/") + f"/storage/v1/object/authenticated/{bucket}/{quote(key, safe='/')}"
    response = httpx.get(url, headers=_headers(), timeout=30)
    response.raise_for_status()
    return response.content


def delete(value: str):
    location = parse(value)
    if not location:
        return
    bucket, key = location
    url = os.environ["SUPABASE_URL"].rstrip("/") + f"/storage/v1/object/{bucket}"
    response = httpx.request("DELETE", url, headers={**_headers(), "Content-Type": "application/json"}, json={"prefixes": [key]}, timeout=15)
    response.raise_for_status()


def put_user_file(bucket: str, suffix: str, content: bytes, content_type=None):
    key = f"{db.current_user()}/{suffix.lstrip('/')}"
    return put(bucket, key, content, content_type)
