"""
Glacier - Local API server (OpenJarvis jaisa OpenAI-compatible endpoint)
Sirf 127.0.0.1 par chalta hai. Token zaroori hai (Authorization: Bearer <token> ya X-Glacier-Token).
Token pehli baar auto-ban jaata hai: data/api_token.txt
Endpoints:  GET /health   POST /ask {"text": "..."}   POST /v1/chat/completions (OpenAI format)
"""

import hmac
import json
import os
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import config
import registry

_server = None
TOKEN_PATH = os.path.join(config.DATA_DIR, "api_token.txt")


def get_token() -> str:
    try:
        with open(TOKEN_PATH, encoding="utf-8") as f:
            t = f.read().strip()
            if t:
                return t
    except OSError:
        pass
    t = secrets.token_urlsafe(24)
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
        f.write(t)
    return t


class Handler(BaseHTTPRequestHandler):
    server_version = "Glacier"

    def log_message(self, *a):
        pass

    def _send(self, code: int, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authed(self) -> bool:
        tok = self.headers.get("X-Glacier-Token") or self.headers.get("Authorization", "").replace("Bearer ", "", 1)
        return bool(tok) and hmac.compare_digest(tok.strip(), get_token())

    def do_GET(self):
        if self.path.rstrip("/") == "/health":
            return self._send(200, {"ok": True, "name": config.ASSISTANT_NAME})
        self._send(404, {"error": "not found"})

    def do_POST(self):
        if not self._authed():
            return self._send(401, {"error": "token galat ya missing"})
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if n > 200_000:
                return self._send(413, {"error": "bahut bada"})
            data = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._send(400, {"error": "bad json"})
        import brain
        path = self.path.split("?")[0].rstrip("/")
        try:
            if path == "/ask":
                reply = brain.ask_glacier(str(data.get("text", "")), session="api")
                return self._send(200, {"reply": reply})
            if path in ("/v1/chat/completions", "/chat/completions"):
                msgs = [m for m in data.get("messages", []) if m.get("role") == "user"]
                last = msgs[-1].get("content", "") if msgs else ""
                if isinstance(last, list):
                    last = " ".join(p.get("text", "") for p in last if isinstance(p, dict))
                reply = brain.ask_glacier(str(last), session="api")
                return self._send(200, {
                    "id": f"chatcmpl-{int(time.time())}", "object": "chat.completion", "created": int(time.time()),
                    "model": "glacier",
                    "choices": [{"index": 0, "message": {"role": "assistant", "content": reply}, "finish_reason": "stop"}],
                })
        except Exception as e:
            registry.log_error("api_server", e)
            return self._send(500, {"error": type(e).__name__})
        self._send(404, {"error": "not found"})


def start():
    global _server
    if _server or not config.API_SERVER_ENABLED:
        return False
    try:
        _server = ThreadingHTTPServer(("127.0.0.1", config.API_SERVER_PORT), Handler)
    except OSError as e:
        registry.log_error("api_server bind", e)
        return False
    get_token()
    threading.Thread(target=_server.serve_forever, daemon=True, name="glacier-api").start()
    return True
