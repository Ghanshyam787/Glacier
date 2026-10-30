"""
Glacier - LLM engines
=====================
Primary : Google Gemini (free tier) via google-genai
Fallback: koi bhi OpenAI-compatible server (Ollama = offline & free, Groq, OpenRouter, LM Studio)

Ye module free-tier ki sabse badi dikkat sambhalta hai: quota / model-name churn.
  * 429 per-minute  -> thoda ruk ke dobara
  * 429 per-day     -> us model ko "aaj ke liye khatam" mark karo, agla model try karo
  * 404 / retired   -> model hata do, agla try karo (aur available models khud discover karo)
  * sab khatam      -> Ollama/Groq (agar configured) warna saaf message ki quota kab reset hoga
"""

import json
import re
import threading
import time
from datetime import datetime, timedelta, timezone

import config
import db
import registry

try:
    from google import genai
    from google.genai import types
except ImportError:  # doctor.py reports this clearly
    genai = None
    types = None

try:
    import requests
except ImportError:
    requests = None


class EngineError(Exception):
    def __init__(self, friendly: str, kind: str = "other"):
        super().__init__(friendly)
        self.friendly = friendly
        self.kind = kind


# --------------------------------------------------------------------------
# Client
# --------------------------------------------------------------------------
_client = None
_client_lock = threading.Lock()


def client():
    global _client
    if genai is None:
        raise EngineError("'google-genai' library install nahi hai. Terminal mein: pip install google-genai", "setup")
    if not config.has_api_key():
        raise EngineError("Gemini API key set nahi hai. .env file mein GEMINI_API_KEY daalo "
                          "(free: https://aistudio.google.com/apikey).", "auth")
    with _client_lock:
        if _client is None:
            _client = genai.Client(api_key=config.GEMINI_API_KEY)
        return _client


# --------------------------------------------------------------------------
# Quota tracking (Gemini daily quota resets at midnight Pacific time)
# --------------------------------------------------------------------------
def _pacific_now() -> datetime:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Los_Angeles"))
    except Exception:
        return datetime.now(timezone(timedelta(hours=-7)))


def _quota_day() -> str:
    return _pacific_now().strftime("%Y-%m-%d")


def quota_reset_local_str() -> str:
    p = _pacific_now()
    nxt = (p + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return nxt.astimezone().strftime("%I:%M %p").lstrip("0")


def usage_add(model: str, n: int = 1):
    try:
        key = f"usage:{_quota_day()}"
        data = json.loads(db.kv_get(key, "{}") or "{}")
        data[model] = data.get(model, 0) + n
        db.kv_set(key, json.dumps(data))
    except Exception:
        pass


def usage_summary() -> dict:
    try:
        data = json.loads(db.kv_get(f"usage:{_quota_day()}", "{}") or "{}")
    except Exception:
        data = {}
    total = sum(data.values())
    return {"used": total, "limit": config.DAILY_REQUEST_LIMIT, "by_model": data,
            "resets_at": quota_reset_local_str()}


_exhausted_mem = set()


def mark_exhausted(model: str):
    _exhausted_mem.add((_quota_day(), model))
    try:
        db.kv_set(f"exhausted:{_quota_day()}:{model}", "1")
    except Exception:
        pass


def is_exhausted(model: str) -> bool:
    if (_quota_day(), model) in _exhausted_mem:
        return True
    try:
        return db.kv_get(f"exhausted:{_quota_day()}:{model}") == "1"
    except Exception:
        return False


# --------------------------------------------------------------------------
# Model selection / discovery
# --------------------------------------------------------------------------
_bad_models = set()
_cooldown = {}
_discovered = None
_discover_lock = threading.Lock()
_EXCLUDE = ("tts", "image", "live", "audio", "embedding", "robotics", "computer", "exp", "latest", "learnlm",
            "gemma", "aqa", "veo", "imagen", "native")


def _version_of(name: str) -> float:
    m = re.search(r"gemini-(\d+(?:\.\d+)?)", name)
    return float(m.group(1)) if m else 0.0


def discover_models(force: bool = False) -> list:
    """Is API key ke liye available Gemini flash models (lite pehle, naye pehle)."""
    global _discovered
    with _discover_lock:
        if _discovered is not None and not force:
            return list(_discovered)
        found = []
        try:
            for m in client().models.list():
                name = (getattr(m, "name", "") or "").replace("models/", "")
                actions = getattr(m, "supported_actions", None) or []
                if not name.startswith("gemini") or "flash" not in name:
                    continue
                if actions and "generateContent" not in actions:
                    continue
                if any(x in name for x in _EXCLUDE):
                    continue
                found.append(name)
        except Exception:
            _discovered = []
            return []
        found = sorted(set(found), key=lambda n: (0 if "lite" in n else 1, 0 if "preview" not in n else 1, -_version_of(n)))
        _discovered = found
        return list(found)


def candidate_models() -> list:
    order, seen = [], set()
    for m in [config.MODEL_NAME] + config.MODEL_FALLBACKS + (list(_discovered) if _discovered else []):
        if m and m not in seen:
            seen.add(m)
            order.append(m)
    return order


def _usable(m: str) -> bool:
    return m not in _bad_models and not is_exhausted(m)


def pick_model():
    """Best available model, ya None agar sab khatam/bad hain."""
    now = time.time()
    cands = candidate_models()
    for m in cands:
        if _usable(m) and _cooldown.get(m, 0) <= now:
            return m
    for m in cands:
        if _usable(m):
            return m
    if config.AUTO_DISCOVER_MODELS and _discovered is None and config.has_api_key():
        discover_models()
        for m in candidate_models():
            if _usable(m):
                return m
    return None


def mark_bad(model: str):
    _bad_models.add(model)


def cooldown(model: str, seconds: float):
    _cooldown[model] = time.time() + seconds


# --------------------------------------------------------------------------
# Error classification
# --------------------------------------------------------------------------
def classify(exc: BaseException) -> dict:
    s = str(exc)
    low = s.lower()
    code = getattr(exc, "code", None)
    if not isinstance(code, int):
        m = re.search(r"\b([45]\d\d)\b", s)
        code = int(m.group(1)) if m else None

    retry = None
    for pat in (r"retry in ([\d.]+)\s*s", r"retrydelay['\"]?\s*[:=]\s*['\"]?(\d+(?:\.\d+)?)s", r"retry after (\d+)"):
        m = re.search(pat, low)
        if m:
            retry = float(m.group(1))
            break

    if "api key not valid" in low or "api_key_invalid" in low or code in (401,) or \
            (code == 403 and "permission" in low) or "api key expired" in low:
        kind = "auth"
    elif code == 429 or "resource_exhausted" in low or "quota" in low and "exceed" in low:
        compact = low.replace(" ", "")
        kind = "daily" if ("perday" in compact or "per day" in low or "daily" in low) else "minute"
    elif code == 404 or "no longer available" in low or "is not found" in low or "not supported for generatecontent" in low:
        kind = "model"
    elif code in (500, 502, 503, 504) or "unavailable" in low or "overloaded" in low or "internal error" in low:
        kind = "transient"
    elif code == 400:
        kind = "badrequest"
    elif any(x in low for x in ("timeout", "timed out", "getaddrinfo", "connection", "name or service", "network",
                                "ssl", "connecterror")) or \
            any(x in type(exc).__name__.lower() for x in ("timeout", "connect", "network")):
        kind = "network"
    else:
        kind = "other"
    return {"kind": kind, "retry": retry, "code": code, "message": s[:300]}


def friendly_for(kind: str, detail: str = "") -> str:
    if kind == "auth":
        return ("Gemini API key galat ya disable lagti hai. .env mein GEMINI_API_KEY dobara check karo "
                "(https://aistudio.google.com/apikey).")
    if kind == "network":
        return "Internet ya Google API se connect nahi ho paa raha. Net check karke dobara try karo."
    if kind in ("daily", "exhausted"):
        return (f"Aaj ka free Gemini quota khatam ho gaya. Quota ~{quota_reset_local_str()} pe reset hota hai. "
                "Tab tak offline chalane ke liye Ollama install karo (README mein 2-minute guide) - "
                "Glacier use khud pehchan lega.")
    if kind == "setup":
        return detail
    return f"Kuchh galat ho gaya: {detail[:200]}" if detail else "Kuchh galat ho gaya."


# --------------------------------------------------------------------------
# One-shot generation (research, digest, vision, screen agent ...)
# --------------------------------------------------------------------------
def generate(contents, system: str = None, json_output: bool = False, temperature: float = 0.4,
             max_attempts: int = 8) -> str:
    """contents: str ya list (str, PIL.Image, types.Part). Fallback chain ke saath. Raises EngineError."""
    last_kind, last_msg = "other", ""
    for _ in range(max_attempts):
        model = pick_model()
        if model is None:
            break
        try:
            cfg = types.GenerateContentConfig(
                system_instruction=system, temperature=temperature,
                response_mime_type="application/json" if json_output else None)
            resp = client().models.generate_content(model=model, contents=contents, config=cfg)
            usage_add(model)
            return _resp_text(resp)
        except EngineError:
            raise
        except Exception as e:
            registry.log_error("engines.generate", e)
            info = classify(e)
            last_kind, last_msg = info["kind"], info["message"]
            k = info["kind"]
            if k == "minute":
                wait = min((info["retry"] or 15) + 1, 45)
                cooldown(model, wait)
                time.sleep(wait if wait <= 20 else 5)
            elif k == "daily":
                mark_exhausted(model)
            elif k == "model":
                mark_bad(model)
            elif k == "transient":
                cooldown(model, 20)
                time.sleep(2)
            else:
                raise EngineError(friendly_for(k, last_msg), k)
    # Gemini ne jawab de diya - ab compat engine (Ollama etc.)
    if compat_config():
        try:
            msgs = ([{"role": "system", "content": system}] if system else []) + \
                   [{"role": "user", "content": contents if isinstance(contents, str) else
                     "\n".join(c for c in contents if isinstance(c, str))}]
            text, _ = compat_chat(msgs, use_tools=False)
            if text:
                return text
        except Exception as e:
            registry.log_error("compat.generate", e)
    raise EngineError(friendly_for("daily" if last_kind in ("daily", "minute", "other") else last_kind, last_msg),
                      last_kind)


def _resp_text(resp) -> str:
    try:
        t = resp.text
        if t:
            return t
    except Exception:
        pass
    out = []
    try:
        for cand in resp.candidates or []:
            for part in (cand.content.parts or []):
                if getattr(part, "text", None):
                    out.append(part.text)
    except Exception:
        pass
    return "".join(out)


def extract_json(text: str):
    """LLM ke text se JSON nikalo (code-fence ya extra text ho tab bhi)."""
    if not text:
        return None
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.I)
    try:
        return json.loads(t)
    except Exception:
        pass
    for open_c, close_c in (("{", "}"), ("[", "]")):
        i, j = t.find(open_c), t.rfind(close_c)
        if i != -1 and j > i:
            try:
                return json.loads(t[i:j + 1])
            except Exception:
                continue
    return None


# --------------------------------------------------------------------------
# OpenAI-compatible engine (Ollama / Groq / OpenRouter / LM Studio)
# --------------------------------------------------------------------------
_ollama_cache = {"t": 0, "val": None}


def compat_config():
    """(base_url, model, api_key) ya None."""
    if config.OPENAI_COMPAT_BASE_URL:
        return config.OPENAI_COMPAT_BASE_URL, config.OPENAI_COMPAT_MODEL, config.OPENAI_COMPAT_API_KEY
    if not config.AUTO_DETECT_OLLAMA or requests is None:
        return None
    now = time.time()
    if now - _ollama_cache["t"] < 60:
        return _ollama_cache["val"]
    val = None
    try:
        r = requests.get("http://127.0.0.1:11434/api/tags", timeout=0.7)
        if r.ok:
            models = [m.get("name") for m in r.json().get("models", []) if m.get("name")]
            import os
            want = os.environ.get("OLLAMA_MODEL") or config.OPENAI_COMPAT_MODEL
            pick = next((m for m in models if m.split(":")[0] == want.split(":")[0]), None) or (models[0] if models else None)
            if pick:
                val = ("http://127.0.0.1:11434/v1", pick, "ollama")
    except Exception:
        val = None
    _ollama_cache.update(t=now, val=val)
    return val


def compat_chat(messages: list, use_tools: bool = True, max_rounds: int = 6):
    """Returns (reply_text, executed_tool_names). Raises on HTTP errors."""
    cfg = compat_config()
    if not cfg or requests is None:
        raise EngineError("Koi backup engine configured nahi hai.", "setup")
    base, model, key = cfg
    schemas = registry.openai_tool_schemas() if use_tools else None
    executed = []
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    url = base.rstrip("/") + "/chat/completions"
    for _ in range(max_rounds):
        payload = {"model": model, "messages": messages, "temperature": 0.4}
        if schemas:
            payload["tools"] = schemas
        r = requests.post(url, json=payload, headers=headers, timeout=180)
        if r.status_code >= 400 and schemas and ("tool" in r.text.lower() or "function" in r.text.lower()):
            schemas = None  # model tools support nahi karta - plain chat
            continue
        r.raise_for_status()
        msg = r.json()["choices"][0]["message"]
        calls = msg.get("tool_calls") or []
        if not calls:
            return (msg.get("content") or "").strip(), executed
        messages.append(msg)
        for c in calls:
            fn = c.get("function", {})
            name = fn.get("name", "")
            raw_args = fn.get("arguments") or "{}"
            try:
                args = raw_args if isinstance(raw_args, dict) else json.loads(raw_args)
            except Exception:
                args = {}
            result = registry.call_tool(name, args)
            executed.append(name)
            messages.append({"role": "tool", "tool_call_id": c.get("id", ""), "name": name, "content": result})
    return "Kaam adhoora reh gaya (tool loop limit).", executed
