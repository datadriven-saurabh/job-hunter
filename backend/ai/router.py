import hashlib
import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from threading import Lock

import httpx

from backend import database as db

CONFIG_PATH = db.ROOT / "config/ai.json"
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
SAFE_FREE_MODELS = (
    "deepseek/deepseek-v4-flash-0731:free",
    "qwen/qwen3.8-27b:free",
)
_catalog_lock = Lock()
_budget_lock = Lock()
_catalog = {"checked_at": 0.0, "models": set()}
_local_budget = {}
_cost_guard_triggered = False


def settings():
    value = json.loads(CONFIG_PATH.read_text())
    saved = (db.config() or {}).get("llm_provider_config", {})
    value["tiers"].update({k: v for k, v in saved.get("model_tiers", {}).items() if v})
    for tier in ["medium", "strong"]:
        if not value["tiers"][tier]:
            value["tiers"][tier] = saved.get("reasoning_model", "qwen3:4b")
    return value


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


class ModelUnavailable(ValueError):
    pass


def provider_name():
    if os.getenv("ENABLE_OPENROUTER") == "true" and os.getenv("OPENROUTER_API_KEY", "").strip():
        return "openrouter"
    if os.getenv("ENABLE_LOCAL_LLM") == "true":
        return "ollama"
    return "none"


def _bounded_env(name, default, maximum):
    try:
        return max(1, min(int(os.getenv(name, str(default))), maximum))
    except ValueError:
        return default


def _openrouter_models():
    requested = [x.strip() for x in os.getenv("OPENROUTER_FREE_MODELS", ",".join(SAFE_FREE_MODELS)).split(",") if x.strip()]
    requested = list(dict.fromkeys(requested))
    if not requested or any(model not in SAFE_FREE_MODELS or not model.endswith(":free") for model in requested):
        raise ModelUnavailable("OpenRouter is restricted to the reviewed free-model allowlist.")
    return requested


def _zero(value):
    try:
        return Decimal(str(value or "0")) == 0
    except InvalidOperation:
        return False


def _verify_free_catalog(models):
    """Fail closed unless OpenRouter currently reports zero input and output price."""
    now = time.monotonic()
    ttl = _bounded_env("OPENROUTER_CATALOG_TTL_SECONDS", 300, 900)
    with _catalog_lock:
        if now - _catalog["checked_at"] <= ttl and set(models) <= _catalog["models"]:
            return
        try:
            response = httpx.get(OPENROUTER_MODELS_URL, timeout=8, follow_redirects=False, trust_env=False)
            response.raise_for_status()
            free = {
                row["id"]
                for row in response.json().get("data", [])
                if isinstance(row, dict)
                and isinstance(row.get("pricing"), dict)
                and _zero(row["pricing"].get("prompt"))
                and _zero(row["pricing"].get("completion"))
            }
        except Exception as exc:
            raise ModelUnavailable("Could not verify zero-cost OpenRouter pricing; cloud AI was not called.") from exc
        _catalog.update(checked_at=now, models=free)
        if not set(models) <= free:
            raise ModelUnavailable("A configured OpenRouter model is no longer confirmed free; cloud AI was not called.")


def _consume_openrouter_budget():
    """Reserve one request before transmission; limits stay below the free allowance."""
    user = db.current_user(required=False) or "local"
    per_user = _bounded_env("MAX_OPENROUTER_REQUESTS_PER_USER_PER_DAY", 8, 20)
    global_limit = _bounded_env("MAX_OPENROUTER_REQUESTS_PER_DAY", 40, 45)
    day = datetime.now(timezone.utc).date().isoformat()
    with _budget_lock:
        if not db.HOSTED:
            user_key = (day, user)
            global_key = (day, "*")
            if _local_budget.get(user_key, 0) >= per_user or _local_budget.get(global_key, 0) >= global_limit:
                raise ModelUnavailable("Daily zero-cost AI allowance reached; deterministic generation remains available.")
            _local_budget[user_key] = _local_budget.get(user_key, 0) + 1
            _local_budget[global_key] = _local_budget.get(global_key, 0) + 1
            return
        used = db.query(
            "SELECT COUNT(*) AS n FROM usage_events WHERE user_id=:user_id AND event_type='OPENROUTER_REQUEST' "
            "AND created_at >= CURRENT_TIMESTAMP - INTERVAL '1 day'",
            {"user_id": user},
        )[0]["n"]
        if used >= per_user:
            raise ModelUnavailable("Your daily zero-cost AI allowance is reached; deterministic generation remains available.")
        key = "openrouter-budget:" + day
        reserved = db.query(
            "INSERT INTO source_cache(cache_key,fetched_at,payload) VALUES (:key,:time,'1') "
            "ON CONFLICT(cache_key) DO UPDATE SET payload=CAST(CAST(source_cache.payload AS INTEGER)+1 AS TEXT),fetched_at=:time "
            "WHERE CAST(source_cache.payload AS INTEGER)<:limit RETURNING payload",
            {"key": key, "time": time.time(), "limit": global_limit},
        )
        if not reserved:
            raise ModelUnavailable("The project's daily zero-cost AI allowance is reached; deterministic generation remains available.")
        db.execute(
            "INSERT INTO usage_events(user_id,event_type) VALUES (:user_id,'OPENROUTER_REQUEST')",
            {"user_id": user},
        )


def _redact_external_prompt(prompt, task):
    if task == "profile_extraction":
        raise ModelUnavailable("Cloud profile extraction is disabled to keep identity details private; review the profile manually or use local Ollama.")
    try:
        context = json.loads(prompt["context"])
    except Exception as exc:
        raise ModelUnavailable("Invalid model context.") from exc
    profile = context.get("USER_PROFILE") if isinstance(context, dict) else None
    personal = profile.get("personal_details", {}) if isinstance(profile, dict) else {}
    exact = [str(personal.get(k, "")).strip() for k in (
        "full_name", "email", "phone", "location", "linkedin_url", "github_url", "portfolio_url", "work_authorization"
    )]
    exact = sorted((v for v in exact if v), key=len, reverse=True)
    private_keys = {"user_id", "personal_details", "eeo_demographics", "email", "phone", "full_name", "linkedin_url", "github_url", "portfolio_url", "work_authorization"}

    def clean(value):
        if isinstance(value, dict):
            return {k: clean(v) for k, v in value.items() if k not in private_keys}
        if isinstance(value, list):
            return [clean(v) for v in value]
        if not isinstance(value, str):
            return value
        result = value
        for item in exact:
            result = re.sub(re.escape(item), "[redacted]", result, flags=re.I)
        result = re.sub(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "[redacted email]", result, flags=re.I)
        result = re.sub(r"https?://[^\s<>'\"]+", "[redacted URL]", result, flags=re.I)
        result = re.sub(r"(?<!\w)(?:\+?\d[\d ().-]{7,}\d)(?!\w)", "[redacted phone]", result)
        return result

    return {"system": prompt["system"], "context": json.dumps(clean(context), ensure_ascii=False, sort_keys=True)}


class ModelRouter:
    def __init__(self, overrides=None):
        self.config = settings()
        if overrides:
            self.config["tiers"].update(overrides)
        self.events = []

    def get(self, task):
        tier = self.config["tasks"][task]
        model = _openrouter_models()[0] if provider_name() == "openrouter" else self.config["tiers"][tier]
        return {"tier": tier, "model": model}

    def _url(self):
        from schemas import LLMProviderConfig
        saved = (db.config() or {}).get("llm_provider_config", {})
        return LLMProviderConfig(**saved).local_ollama_base_url.rstrip("/")

    def _log(self, event):
        self.events.append(event)
        path = db.user_data_path("ai-usage.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as stream:
            stream.write(json.dumps(dict(event, created_at=datetime.now(timezone.utc).isoformat())) + "\n")

    def _identity(self, model):
        if provider_name() == "openrouter":
            if model not in _openrouter_models():
                raise ModelUnavailable("Model is outside the zero-cost allowlist.")
            return "openrouter:" + model
        if os.getenv("ENABLE_LOCAL_LLM") != "true":
            raise ModelUnavailable("AI disabled.")
        try:
            response = httpx.get(self._url() + "/api/tags", timeout=3, trust_env=False)
            response.raise_for_status()
            found = next((m for m in response.json().get("models", []) if m["name"] == model or m["name"] == model + ":latest"), None)
            if found:
                return found.get("digest") or found["name"]
        except Exception:
            pass
        raise ModelUnavailable("Configured local model is not installed or Ollama is unavailable: " + str(model))

    def _openrouter_run(self, task, prompt, schema):
        global _cost_guard_triggered
        if _cost_guard_triggered:
            raise ModelUnavailable("Cloud AI stopped because a nonzero-cost response was reported.")
        models = _openrouter_models()
        _verify_free_catalog(models)
        safe_prompt = _redact_external_prompt(prompt, task)
        _consume_openrouter_budget()
        key = os.environ["OPENROUTER_API_KEY"].strip()
        if not re.fullmatch(r"sk-or-v1-[A-Za-z0-9_-]{20,}", key):
            raise ModelUnavailable("OpenRouter credential format is invalid.")
        body = {
            "models": models,
            "messages": [
                {"role": "system", "content": safe_prompt["system"]},
                {"role": "user", "content": safe_prompt["context"]},
            ],
            "temperature": 0,
            "max_tokens": min(int(self.config["output_tokens"]), 2000),
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": schema.__name__[:60], "strict": True, "schema": schema.model_json_schema()},
            },
            "provider": {"allow_fallbacks": True, "require_parameters": True},
            "usage": {"include": True},
        }
        headers = {"Authorization": "Bearer " + key, "Content-Type": "application/json", "X-Title": "Job Hunter"}
        if os.getenv("APP_URL", "").startswith("https://"):
            headers["HTTP-Referer"] = os.environ["APP_URL"].rstrip("/")
        response = httpx.post(OPENROUTER_CHAT_URL, headers=headers, json=body, timeout=self.config["timeout_seconds"], follow_redirects=False, trust_env=False)
        response.raise_for_status()
        raw = response.json()
        cost = (raw.get("usage") or {}).get("cost", 0)
        if not _zero(cost):
            _cost_guard_triggered = True
            raise ModelUnavailable("Cloud AI stopped after the provider reported a nonzero-cost response.")
        content = raw["choices"][0]["message"]["content"]
        if not isinstance(content, str) or len(content) > 200_000:
            raise ModelUnavailable("OpenRouter returned an invalid response.")
        return schema.model_validate_json(content), raw

    def run(self, task, prompt, schema, *, validator=None):
        provider = provider_name()
        if provider == "none":
            raise ModelUnavailable("AI is disabled; evidence-only generation is available.")
        route = self.get(task)
        tier = route["tier"]
        candidates = [(tier, route["model"]), (tier, route["model"])]
        if provider == "ollama" and tier == "small" and self.config["tiers"]["medium"] != route["model"]:
            candidates.append(("medium", self.config["tiers"]["medium"]))
        if provider == "openrouter":
            candidates = [(tier, route["model"])]
        errors = []
        for attempt, (used_tier, used_model) in enumerate(candidates):
            started = time.monotonic()
            event = {"task": task, "provider": provider, "tier": used_tier, "model": used_model, "retry_count": attempt, "fallback_used": used_tier != tier, "cache_hit": False, "input_tokens": 0, "output_tokens": 0}
            try:
                identity = self._identity(used_model)
                key = digest([self.config["version"], prompt, provider, used_model, identity, schema.model_json_schema()])
                path = db.user_data_path("ai-cache", f"{key}.json")
                if getattr(self, "cache_enabled", True) and path.exists():
                    result = schema.model_validate(json.loads(path.read_text()))
                    if validator:
                        validator(result)
                    event.update(cache_hit=True, latency_ms=0, prompt_version=prompt["version"])
                    self._log(event)
                    return result
                if provider == "openrouter":
                    result, raw = self._openrouter_run(task, prompt, schema)
                    usage = raw.get("usage") or {}
                    event.update(model=raw.get("model", used_model), input_tokens=usage.get("prompt_tokens", 0), output_tokens=usage.get("completion_tokens", 0))
                else:
                    body = {"model": used_model, "system": prompt["system"], "prompt": prompt["context"] + ("\nValidation feedback: " + errors[-1] if errors else ""), "stream": False, "format": schema.model_json_schema(), "options": {"temperature": 0, "num_ctx": self.config["context_tokens"], "num_predict": self.config["output_tokens"]}, "keep_alive": "5m"}
                    if used_model.startswith(("qwen3", "nemotron-3-nano")):
                        body["think"] = False
                    response = httpx.post(self._url() + "/api/generate", json=body, timeout=self.config["timeout_seconds"], trust_env=False)
                    response.raise_for_status()
                    raw = response.json()
                    result = schema.model_validate_json(raw["response"])
                    event.update(input_tokens=raw.get("prompt_eval_count", 0), output_tokens=raw.get("eval_count", 0))
                if validator:
                    validator(result)
                if getattr(self, "cache_enabled", True):
                    path.parent.mkdir(parents=True, exist_ok=True)
                    tmp = path.with_suffix("." + uuid.uuid4().hex + ".tmp")
                    tmp.write_text(result.model_dump_json())
                    tmp.replace(path)
                event.update(prompt_version=prompt["version"], model_version=identity, latency_ms=round((time.monotonic() - started) * 1000))
                self._log(event)
                return result
            except Exception as exc:
                errors.append("Output failed schema or evidence validation; use only the supplied evidence and required fields.")
                event.update(status="failed", error_type=type(exc).__name__, latency_ms=round((time.monotonic() - started) * 1000))
                self._log(event)
                if isinstance(exc, ModelUnavailable):
                    break
        raise ModelUnavailable("No validated model output was available. Use verified evidence or review missing fields.")

    def embed(self, text):
        if provider_name() == "openrouter":
            raise ModelUnavailable("Cloud embeddings are disabled; deterministic private matching is used.")
        if os.getenv("ENABLE_LOCAL_LLM") != "true":
            raise ModelUnavailable("Local AI disabled.")
        route = self.get("embeddings")
        identity = self._identity(route["model"])
        key = digest(["embedding-v1", text, identity])
        path = db.user_data_path("ai-cache", f"{key}.json")
        started = time.monotonic()
        hit = path.exists()
        if hit:
            vector = json.loads(path.read_text())
        else:
            response = httpx.post(self._url() + "/api/embed", json={"model": route["model"], "input": text, "truncate": False}, timeout=self.config["timeout_seconds"], trust_env=False)
            response.raise_for_status()
            vector = response.json()["embeddings"][0]
            if not vector or not all(isinstance(x, (float, int)) for x in vector):
                raise ValueError("Invalid embedding")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(vector))
        self._log({"task": "embeddings", "provider": "ollama", **route, "cache_hit": hit, "latency_ms": round((time.monotonic() - started) * 1000), "model_version": identity})
        return vector
