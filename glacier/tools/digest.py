"""
Glacier Tool: Morning digest (OpenJarvis 'morning_digest' jaisa)
Mausam + khabrein + aaj ke events + to-dos + reminders + PC health -> ek chhota bola jaane layak briefing.
Scheduler ise roz subah chalata hai (config.DIGEST_TIME / pehli baar start hone par).
"""

import time
from datetime import datetime, timedelta

import config
import db
import engines
from registry import tool
from tools import info, productivity, system


def _raw(fn):
    return getattr(fn, "__wrapped__", fn)


def gather() -> dict:
    now = datetime.now()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    data = {"now": now.strftime("%A, %d %B %Y, %I:%M %p")}
    try:
        data["weather"] = _raw(info.weather)("", 2)
    except Exception as e:
        data["weather"] = f"(mausam nahi mila: {e})"
    try:
        data["news"] = [t for t, _s, _d in info.fetch_headlines("", 5)]
    except Exception as e:
        data["news"] = [f"(khabrein nahi mili: {e})"]
    ev = productivity.events_between(day_start.timestamp(), (day_start + timedelta(days=1)).timestamp())
    data["events"] = [f"{datetime.fromtimestamp(r['start']).strftime('%I:%M %p').lstrip('0')} {r['title']}" for r in ev]
    data["todos"] = [r["text"] for r in db.query("SELECT text FROM todos WHERE done=0 ORDER BY id LIMIT 8")]
    rem = db.query("SELECT text,fire_at FROM reminders WHERE fired=0 AND fire_at<? ORDER BY fire_at LIMIT 8",
                   ((day_start + timedelta(days=1)).timestamp(),))
    data["reminders"] = [f"{datetime.fromtimestamp(r['fire_at']).strftime('%I:%M %p').lstrip('0')} {r['text']}" for r in rem]
    try:
        v = system.get_vitals()
        data["pc"] = f"battery {v['battery']}%{' (charging)' if v.get('plugged') else ''}" if v["battery"] is not None else "desktop PC"
    except Exception:
        data["pc"] = ""
    if config.EMAIL_ADDRESS and config.EMAIL_APP_PASSWORD:
        try:
            from tools import comms
            m = comms._imap()
            try:
                m.select("INBOX", readonly=True)
                typ, d = m.search(None, "UNSEEN")
                data["unread_emails"] = len(d[0].split()) if typ == "OK" and d and d[0] else 0
            finally:
                m.logout()
        except Exception:
            pass
    return data


def _fallback_text(d: dict) -> str:
    parts = [f"Good morning {config.USER_ADDRESS}!", d["weather"].split("\n")[0]]
    if d["events"]:
        parts.append("Aaj ke events: " + "; ".join(d["events"]))
    if d["todos"]:
        parts.append("Pending kaam: " + "; ".join(d["todos"][:4]))
    if d["news"]:
        parts.append("Khabrein: " + "; ".join(d["news"][:3]))
    return " ".join(parts)


def build_digest() -> str:
    d = gather()
    prompt = (
        f"Tum {config.ASSISTANT_NAME} ho. {config.USER_NAME} ke liye subah ka briefing likho - Hinglish, natural bolchaal, "
        "6-9 chhote vaakya, bolne layak (markdown/emoji/list nahi). Pehle greeting + mausam, phir aaj ke events/"
        "reminders/kaam, phir 2-3 sabse zaroori khabrein, last mein ek line PC/battery ya email ki agar kaam ki ho. "
        "Jo data diya hai sirf wahi use karo, kuchh invent mat karo.\n\nDATA:\n" +
        "\n".join(f"{k}: {v}" for k, v in d.items()))
    try:
        return engines.generate(prompt, temperature=0.5).strip()
    except engines.EngineError:
        return _fallback_text(d)


@tool(category="agent", label="Morning digest")
def morning_digest() -> str:
    """Give the user a spoken-style briefing: weather, today's events/reminders/to-dos, top news and PC status."""
    db.kv_set("digest_last_date", time.strftime("%Y-%m-%d"))
    return build_digest()
