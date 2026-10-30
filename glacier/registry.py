"""
Glacier - Tool registry
=======================
Har tool @tool decorator se register hota hai. Decorator ye sab khud sambhalta hai:
  * kisi bhi tool ka exception kabhi poore Glacier ko crash nahi karta (error string wapas jaati hai)
  * secrets redact, output truncate, untrusted content (web/email/files) pe injection-warning
  * audit log (data/audit.log) + dashboard ka "Recent activity"
  * config.DISABLED_TOOLS / DISABLED_CATEGORIES se koi bhi tool band kiya ja sakta hai
"""

import functools
import inspect
import json
import os
import threading
import time
import traceback

import activity
import config
import safety

TOOLS = {}          # name -> info dict
_audit_lock = threading.Lock()
_turn_tls = threading.local()


def _turn_log() -> list:
    if not hasattr(_turn_tls, "executed"):
        _turn_tls.executed = []
    return _turn_tls.executed


def begin_turn():
    """Brain har user-message se pehle call karta hai: is turn mein kaun se tools chale, track karne ke liye."""
    _turn_tls.executed = []


def executed_this_turn() -> list:
    return list(_turn_log())


def _short(v, n=60) -> str:
    s = str(v).replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def _audit(entry: dict):
    try:
        with _audit_lock:
            path = config.AUDIT_LOG
            if os.path.exists(path) and os.path.getsize(path) > 2_000_000:
                os.replace(path, path + ".1")
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def log_error(where: str, exc: BaseException):
    try:
        with _audit_lock:
            with open(config.ERROR_LOG, "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {where}\n")
                f.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
                f.write("\n")
    except Exception:
        pass


def is_enabled(name: str, category: str) -> bool:
    return name not in config.DISABLED_TOOLS and category not in config.DISABLED_CATEGORIES


def tool(category: str = "general", dangerous: bool = False, untrusted: str = "", label: str = "",
         quiet: bool = False):
    """
    category : apps | files | system | web | info | memory | productivity | comms | vision | control |
               browser | terminal | schedule | agent | mcp | skill
    dangerous: sirf documentation ke liye (asli gate tool ke andar confirm_gate se hota hai)
    untrusted: agar output bahar ki duniya se aata hai (web/email/file), source ka naam do
    quiet    : True = activity feed mein na dikhao (jaise get_datetime)
    """
    def decorator(fn):
        name = fn.__name__
        pretty = label or name.replace("_", " ")

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if not is_enabled(name, category):
                return f"'{name}' tool config mein disable hai (DISABLED_TOOLS / DISABLED_CATEGORIES)."
            started = time.time()
            ok = True
            try:
                result = fn(*args, **kwargs)
            except Exception as e:  # tools must never crash the brain
                ok = False
                log_error(f"tool {name}", e)
                result = f"{name} mein error aaya: {type(e).__name__}: {str(e)[:300]}"
            if result is None:
                result = "(done)"
            if not isinstance(result, str):
                try:
                    result = json.dumps(result, ensure_ascii=False, default=str, indent=1)
                except Exception:
                    result = str(result)
            result = safety.redact(result)
            if len(result) > config.MAX_TOOL_OUTPUT:
                result = result[: config.MAX_TOOL_OUTPUT] + f"\n…(output kaata gaya, {len(result)} chars the)"
            if untrusted and ok and not result.startswith(("CONFIRMATION_NEEDED", "CANCELLED", "NOT_CONFIRMED")):
                result = safety.wrap_untrusted(result, untrusted)

            arg_repr = {}
            try:
                bound = inspect.signature(fn).bind_partial(*args, **kwargs)
                arg_repr = {k: _short(safety.redact(str(v)), 200) for k, v in bound.arguments.items()}
            except Exception:
                pass
            try:
                _audit({"ts": round(started, 2), "session": safety.get_session(), "tool": name,
                        "args": arg_repr, "ok": ok, "ms": int((time.time() - started) * 1000),
                        "result": _short(result, 200)})
            except Exception:
                pass
            try:
                _turn_log().append({"tool": name, "args": arg_repr, "ok": ok, "result": _short(result, 300)})
            except Exception:
                pass

            if not quiet:
                first = result.split("\n", 1)[0]
                if result.startswith("CONFIRMATION_NEEDED"):
                    activity.add_activity(f"Waiting for your OK: {pretty}", name)
                elif not first.startswith(("CANCELLED", "NOT_CONFIRMED")):
                    activity.add_activity(f"{pretty}: {_short(first, 70)}", name)
            return result

        TOOLS[name] = {
            "fn": wrapper, "raw": fn, "category": category, "dangerous": dangerous,
            "doc": inspect.getdoc(fn) or "", "name": name,
        }
        wrapper.glacier_tool = True
        return wrapper

    return decorator


# --------------------------------------------------------------------------
def all_tool_functions() -> list:
    return [t["fn"] for t in TOOLS.values() if is_enabled(t["name"], t["category"])]


def tools_by_category() -> dict:
    out = {}
    for t in TOOLS.values():
        if is_enabled(t["name"], t["category"]):
            out.setdefault(t["category"], []).append(t["name"])
    return out


def call_tool(name: str, arguments: dict) -> str:
    info = TOOLS.get(name)
    if not info:
        return f"'{name}' naam ka koi tool nahi hai."
    try:
        return info["fn"](**(arguments or {}))
    except TypeError as e:
        return f"{name} ke arguments galat hain: {e}"


_JSON_TYPES = {str: "string", int: "integer", float: "number", bool: "boolean", list: "array", dict: "object"}


def _json_type(annotation) -> str:
    if annotation in _JSON_TYPES:
        return _JSON_TYPES[annotation]
    origin = getattr(annotation, "__origin__", None)
    if origin in _JSON_TYPES:
        return _JSON_TYPES[origin]
    return "string"


def openai_tool_schemas() -> list:
    """OpenAI/Ollama-style function schemas (non-Gemini engines ke liye)."""
    schemas = []
    for t in TOOLS.values():
        if not is_enabled(t["name"], t["category"]):
            continue
        sig = inspect.signature(t["raw"])
        props, required = {}, []
        for pname, p in sig.parameters.items():
            if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
                continue
            jt = _json_type(p.annotation if p.annotation is not inspect.Parameter.empty else str)
            entry = {"type": jt}
            if jt == "array":
                entry["items"] = {"type": "string"}
            props[pname] = entry
            if p.default is inspect.Parameter.empty:
                required.append(pname)
        desc = (t["doc"].split("\n\n")[0] or t["name"]).replace("\n", " ")[:700]
        schemas.append({"type": "function", "function": {
            "name": t["name"], "description": desc,
            "parameters": {"type": "object", "properties": props, "required": required},
        }})
    return schemas
