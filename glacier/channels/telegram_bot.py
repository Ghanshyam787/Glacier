"""
Glacier - Telegram channel (phone se Glacier ko command do)
Sirf `requests` use hota hai (extra library nahi). Sirf TELEGRAM_ALLOWED_CHAT_ID ka chat sunta hai.
Setup: @BotFather se bot banao -> token .env mein TELEGRAM_BOT_TOKEN; bot ko /start bhejo; Glacier tumhara chat id
batayega (aur .env mein TELEGRAM_ALLOWED_CHAT_ID daalna hai).
"""

import os
import threading
import time

import requests

import config
import registry

_API = "https://api.telegram.org/bot{token}/{method}"
_started = False
_stop = threading.Event()


def _call(method: str, data=None, files=None, timeout=35):
    r = requests.post(_API.format(token=config.TELEGRAM_BOT_TOKEN, method=method), data=data, files=files, timeout=timeout)
    return r.json()


def _chat_id():
    return config.TELEGRAM_ALLOWED_CHAT_ID.strip()


def send_text(text: str, chat_id: str = None) -> str:
    if not config.TELEGRAM_BOT_TOKEN:
        return "Telegram bot token set nahi hai (.env: TELEGRAM_BOT_TOKEN)."
    cid = chat_id or _chat_id()
    if not cid:
        return "TELEGRAM_ALLOWED_CHAT_ID set nahi hai. Bot ko /start bhejo, wo chat id bata dega."
    try:
        for i in range(0, len(text) or 1, 3800):
            res = _call("sendMessage", {"chat_id": cid, "text": text[i:i + 3800]})
            if not res.get("ok"):
                return f"Telegram error: {res.get('description', '?')}"
        return "Telegram par bhej diya."
    except Exception as e:
        return f"Telegram bhej nahi paya: {type(e).__name__}"


def send_file(path: str, chat_id: str = None) -> str:
    if not config.TELEGRAM_BOT_TOKEN or not (chat_id or _chat_id()):
        return "Telegram set nahi hai (.env: TELEGRAM_BOT_TOKEN aur TELEGRAM_ALLOWED_CHAT_ID)."
    cid = chat_id or _chat_id()
    if os.path.getsize(path) > 49 * 1024 * 1024:
        return "File 50 MB se badi hai, Telegram nahi lega."
    try:
        method = "sendPhoto" if path.lower().endswith((".png", ".jpg", ".jpeg")) else "sendDocument"
        field = "photo" if method == "sendPhoto" else "document"
        with open(path, "rb") as f:
            res = _call(method, {"chat_id": cid}, {field: f}, timeout=120)
        return "Phone par bhej di." if res.get("ok") else f"Telegram error: {res.get('description', '?')}"
    except Exception as e:
        return f"Telegram bhej nahi paya: {type(e).__name__}"


def _download(file_id: str, dest: str) -> bool:
    info = _call("getFile", {"file_id": file_id})
    if not info.get("ok"):
        return False
    url = f"https://api.telegram.org/file/bot{config.TELEGRAM_BOT_TOKEN}/{info['result']['file_path']}"
    r = requests.get(url, timeout=60)
    with open(dest, "wb") as f:
        f.write(r.content)
    return True


def _handle(msg: dict):
    import brain
    cid = str(msg["chat"]["id"])
    text = (msg.get("text") or msg.get("caption") or "").strip()
    allowed = _chat_id()
    if text.startswith("/start") and not allowed:
        send_text(f"Tumhara chat id: {cid}\n.env mein ye line daalo aur Glacier restart karo:\nTELEGRAM_ALLOWED_CHAT_ID={cid}", cid)
        return
    if cid != allowed:
        return  # anjaan log: chupchap ignore
    low = text.lower()
    if low.startswith("/stop"):
        try:
            import voice
            voice.stop_speaking()
            from tools import control
            control.stop_all_actions()
        except Exception:
            pass
        send_text("Rok diya.", cid)
        return
    if low.startswith("/status"):
        s = brain.status()
        send_text(f"Model: {s['model']}\nQuota: {s['quota_used']}/{s['quota_limit']}\nTools: {s['tools']}", cid)
        return
    if low.startswith("/screenshot"):
        try:
            import imgutil
            p = imgutil.save_screenshot()
            send_file(p, cid)
        except Exception as e:
            send_text(f"Screenshot nahi ho paya: {type(e).__name__}", cid)
        return
    if low.startswith("/reset"):
        brain.reset_session("telegram")
        send_text("Nayi baat-cheet shuru.", cid)
        return

    images = None
    tmpdir = os.path.join(config.DATA_DIR, "tmp")
    os.makedirs(tmpdir, exist_ok=True)
    if msg.get("photo"):
        p = os.path.join(tmpdir, f"tg_{int(time.time())}.jpg")
        if _download(msg["photo"][-1]["file_id"], p):
            images = [p]
            text = text or "Is photo mein kya hai?"
    elif msg.get("voice") or msg.get("audio"):
        try:
            import voice
            fid = (msg.get("voice") or msg.get("audio"))["file_id"]
            p = os.path.join(tmpdir, f"tg_{int(time.time())}.ogg")
            if _download(fid, p):
                text = voice.transcribe_file(p) or ""
        except Exception as e:
            registry.log_error("telegram voice", e)
        if not text:
            send_text("Voice samajh nahi aayi. Text mein likh do.", cid)
            return
    if not text and not images:
        return
    reply = brain.ask_glacier(text, session="telegram", images=images)
    send_text(reply or "(khaali jawab)", cid)


def _poll():
    offset = 0
    fails = 0
    while not _stop.is_set():
        try:
            res = _call("getUpdates", {"offset": offset, "timeout": 25}, timeout=35)
            if not res.get("ok"):
                raise RuntimeError(res.get("description", "getUpdates fail"))
            fails = 0
            for upd in res.get("result", []):
                offset = upd["update_id"] + 1
                msg = upd.get("message")
                if msg:
                    threading.Thread(target=_safe_handle, args=(msg,), daemon=True).start()
        except Exception as e:
            fails += 1
            if fails in (1, 10):
                registry.log_error("telegram poll", e)
            time.sleep(min(60, 3 * fails))


def _safe_handle(msg):
    try:
        _handle(msg)
    except Exception as e:
        registry.log_error("telegram handle", e)


def start():
    global _started
    if _started or not config.TELEGRAM_BOT_TOKEN:
        return False
    _started = True
    threading.Thread(target=_poll, daemon=True, name="glacier-telegram").start()
    return True
