"""
Glacier Tools: Reminders, timers and scheduled tasks
Reminders/timers/tasks SQLite mein rehte hain; scheduler.py unhe time par chalata hai.

Bug-fixes vs. old version:
  * month-end par 'kal' wala reminder crash karta tha (day=now.day+1) - ab timedelta
  * ab "in 10 minutes", "kal 9 baje", "monday 5pm", roz/weekdays repeat sab chalta hai
  * corrupt JSON / thread race khatam (SQLite)
"""

import json
import os
import time
from datetime import datetime

import config
import db
import timeparse
from registry import tool

# ---- one-time import of the old reminders.json (V1-V3) -----------------------------------
_LEGACY = os.path.join(config.BASE_DIR, "reminders.json")


def _migrate_legacy():
    try:
        if db.kv_get("legacy_reminders_imported") or not os.path.exists(_LEGACY):
            return
        with open(_LEGACY, encoding="utf-8") as f:
            for r in json.load(f):
                if not r.get("fired"):
                    ts = datetime.fromisoformat(r["fire_at"]).timestamp()
                    db.execute("INSERT INTO reminders(text,fire_at,recur,fired,created) VALUES(?,?,?,?,?)",
                               (r["text"], ts, "", 0, time.time()))
        db.kv_set("legacy_reminders_imported", "1")
    except Exception:
        pass


_migrate_legacy()


# ---- helpers used by GUI / scheduler ---------------------------------------------------
def get_reminders_list() -> list:
    """GUI ke Reminders card ke liye (sirf aane wale): [{'text','time'}]."""
    rows = db.query("SELECT text,fire_at FROM reminders WHERE fired=0 ORDER BY fire_at LIMIT 12")
    now = datetime.now()
    out = []
    for r in rows:
        dt = datetime.fromtimestamp(r["fire_at"])
        out.append({"text": r["text"], "time": dt.strftime("%H:%M") if dt.date() == now.date() else timeparse.human(dt, now)})
    return out


_VIEWS = ("all", "upcoming", "done", "missed", "repeat")


def _status_of(r) -> str:
    if not r["fired"]:
        return "upcoming"
    return "missed" if (r["status"] or "") == "missed" else "done"


def _repeat_label(rep: str) -> str:
    if not rep:
        return ""
    if rep.startswith("every:"):
        m = int(rep.split(":")[1])
        return f"har {m // 60} ghante" if m % 60 == 0 else f"har {m} minute"
    return {"daily": "roz", "weekly": "har hafte", "weekdays": "Mon-Fri"}.get(rep, rep)


def reminders_all(view: str = "all") -> list:
    """Manager panel ke liye: shuru se saare reminders (aane wale, ho chuke, chhoote), naye/aane wale pehle."""
    view = view if view in _VIEWS else "all"
    rows = db.query("SELECT * FROM reminders ORDER BY fire_at")
    now = datetime.now()
    out = []
    for r in rows:
        st = _status_of(r)
        if view == "repeat" and not r["recur"]:
            continue
        if view in ("upcoming", "done", "missed") and st != view:
            continue
        dt = datetime.fromtimestamp(r["fire_at"])
        out.append({"id": r["id"], "text": r["text"], "status": st, "repeat": r["recur"] or "", "repeat_label": _repeat_label(r["recur"] or ""),
                    "when": dt.strftime("%Y-%m-%d %H:%M"), "when_human": dt.strftime("%a %d %b %Y, %I:%M %p").replace(" 0", " "),
                    "created": datetime.fromtimestamp(r["created"]).strftime("%d %b %Y") if r["created"] else ""})
    up = [x for x in out if x["status"] == "upcoming"]
    past = [x for x in out if x["status"] != "upcoming"][::-1]       # purane niche, taaza upar
    return up + past


def _check_repeat(repeat: str):
    rep = timeparse.normalize_repeat(repeat)
    if (repeat or "").strip() and not rep and (repeat or "").strip().lower() not in ("no", "none", "once", "nahi"):
        return None
    return rep


def reminder_add(text: str, when: str, repeat: str = "") -> dict:
    text = (text or "").strip()
    if not text:
        return {"ok": False, "msg": "Reminder ka text likho."}
    dt = timeparse.parse_when(when)
    if dt is None:
        return {"ok": False, "msg": "Time samajh nahi aaya. Jaise: 7pm, kal 9 baje, in 10 minutes, 2026-11-20 08:30"}
    rep = _check_repeat(repeat)
    if rep is None:
        return {"ok": False, "msg": "Repeat samajh nahi aaya (daily, weekdays, weekly, every 30 minutes)."}
    cur = db.execute("INSERT INTO reminders(text,fire_at,recur,fired,created,status) VALUES(?,?,?,?,?,'')",
                     (text, dt.timestamp(), rep, 0, time.time()))
    return {"ok": True, "id": cur.lastrowid, "msg": f"Reminder set: {timeparse.human(dt)}"}


def reminder_update(rid: int, text: str, when: str, repeat: str = "") -> dict:
    r = db.query_one("SELECT * FROM reminders WHERE id=?", (int(rid),))
    if not r:
        return {"ok": False, "msg": "Ye reminder nahi mila (shayad delete ho chuka)."}
    text = (text or "").strip() or r["text"]
    dt = timeparse.parse_when(when) if (when or "").strip() else datetime.fromtimestamp(r["fire_at"])
    if dt is None:
        return {"ok": False, "msg": "Time samajh nahi aaya. Jaise: 7pm, kal 9 baje, 2026-11-20 08:30"}
    rep = _check_repeat(repeat if repeat is not None else r["recur"])
    if rep is None:
        return {"ok": False, "msg": "Repeat samajh nahi aaya."}
    rearm = dt.timestamp() > time.time()
    if rearm or not r["fired"]:
        db.execute("UPDATE reminders SET text=?, fire_at=?, recur=?, fired=?, status='', done_at=NULL WHERE id=?",
                   (text, dt.timestamp(), rep, 0 if rearm else r["fired"], r["id"]))
    else:  # purana (ho chuka) reminder, time ab bhi beet chuka -> sirf text/repeat badlo
        db.execute("UPDATE reminders SET text=?, recur=? WHERE id=?", (text, rep, r["id"]))
    return {"ok": True, "msg": "Badal diya." + ("" if rearm or not r["fired"] else " (Time beet chuka hai, isliye dobara active nahi hua - naya aane wala time do.)")}


def reminder_delete(rid: int) -> dict:
    r = db.query_one("SELECT id FROM reminders WHERE id=?", (int(rid),))
    if not r:
        return {"ok": False, "msg": "Ye reminder pehle hi nahi hai."}
    db.execute("DELETE FROM reminders WHERE id=?", (int(rid),))
    return {"ok": True, "msg": "Delete ho gaya."}


def _find(which: str, table: str, col: str):
    which = (which or "").strip()
    if which.isdigit():
        return db.query_one(f"SELECT * FROM {table} WHERE id=?", (int(which),))
    return db.query_one(f"SELECT * FROM {table} WHERE {col} LIKE ? ORDER BY id DESC", (f"%{which}%",))


# ---- tools ------------------------------------------------------------------------------
@tool(category="schedule", label="Add reminder")
def add_reminder(text: str, when: str, repeat: str = "") -> str:
    """
    Set a reminder. 'when' can be natural: '19:00', '7pm', 'in 10 minutes', 'kal 9 baje', 'monday 5:30pm',
    '2026-10-25 08:00'. Optional repeat: daily | weekdays | weekly | 'every 30 minutes'.
    """
    dt = timeparse.parse_when(when)
    if dt is None:
        return ("Time samajh nahi aaya. Aise batao: '7pm', '19:30', 'in 10 minutes', 'kal 9 baje', "
                "'monday 5pm'.")
    rep = timeparse.normalize_repeat(repeat)
    cur = db.execute("INSERT INTO reminders(text,fire_at,recur,fired,created,status) VALUES(?,?,?,?,?,'')",
                     (text.strip(), dt.timestamp(), rep, 0, time.time()))
    rep_txt = f", repeat: {rep}" if rep else ""
    return f"Reminder #{cur.lastrowid} set: '{text.strip()}' - {timeparse.human(dt)}{rep_txt}"


@tool(category="schedule", label="List reminders")
def list_reminders(include_history: bool = False) -> str:
    """List upcoming reminders and running timers. include_history=True also shows every past reminder (done and missed) since the beginning."""
    if include_history:
        items = reminders_all("all")
        if not items:
            return "Abhi tak koi reminder nahi diya gaya."
        names = {"upcoming": "aane wala", "done": "ho chuka", "missed": "CHHOOT GAYA"}
        return "Saare reminders (shuru se):\n" + "\n".join(
            f"#{x['id']} [{names[x['status']]}] {x['text']} - {x['when_human']}" + (f" ({x['repeat_label']})" if x["repeat_label"] else "") for x in items)
    rows = db.query("SELECT id,text,fire_at,recur FROM reminders WHERE fired=0 ORDER BY fire_at")
    if not rows:
        return "Koi reminder set nahi hai."
    return "Upcoming reminders:\n" + "\n".join(
        f"#{r['id']} {r['text']} - {timeparse.human(datetime.fromtimestamp(r['fire_at']))}"
        f"{' (' + r['recur'] + ')' if r['recur'] else ''}" for r in rows)


@tool(category="schedule", label="Edit reminder")
def edit_reminder(which: str, text: str = "", when: str = "", repeat: str = "") -> str:
    """Change an existing reminder (find it by #id or words in its text): new text, new time ('kal 9 baje', '7pm') and/or new repeat. Leave a field empty to keep it. A missed reminder with a new future time becomes active again."""
    r = _find(which, "reminders", "text")
    if not r:
        return f"'{which}' naam ka koi reminder nahi mila."
    res = reminder_update(r["id"], text, when, repeat if repeat else (r["recur"] or ""))
    return res["msg"]


@tool(category="schedule", label="Cancel reminder")
def cancel_reminder(which: str) -> str:
    """Cancel a reminder by its number (#id) or by words from its text."""
    r = _find(which, "reminders", "text")
    if not r:
        return f"'{which}' naam ka koi reminder nahi mila."
    db.execute("DELETE FROM reminders WHERE id=?", (r["id"],))
    return f"Reminder cancel kar diya: {r['text']}"


@tool(category="schedule", label="Set timer")
def set_timer(duration: str, label: str = "") -> str:
    """Start a countdown timer, e.g. duration='10 minutes', '1h30m', '45 sec'. Glacier announces when it ends."""
    secs = timeparse.parse_duration(duration)
    if not secs or secs <= 0:
        return "Duration samajh nahi aayi (jaise '10 minutes' ya '1h30m')."
    if secs > 24 * 3600:
        return "Timer 24 ghante se zyada ka nahi ho sakta - reminder use karo."
    text = f"Timer khatam: {label}" if label else "Timer khatam!"
    cur = db.execute("INSERT INTO reminders(text,fire_at,recur,fired,created,status) VALUES(?,?,?,?,?,'')",
                     (text, time.time() + secs, "", 0, time.time()))
    m, s = divmod(int(secs), 60)
    return f"Timer #{cur.lastrowid} start: {m} min {s} sec." if s else f"Timer #{cur.lastrowid} start: {m} min."


# ---- scheduled agent tasks --------------------------------------------------------------
@tool(category="schedule", label="Schedule task")
def schedule_task(prompt: str, when: str, repeat: str = "", name: str = "") -> str:
    """
    Schedule Glacier itself to do something later or repeatedly (like a cron job): at the given time Glacier
    runs 'prompt' as if the user typed it and announces the result. Example: prompt='Aaj ki top 5 AI news
    batao', when='08:30', repeat='daily'. Dangerous actions inside scheduled tasks still need the user's OK.
    """
    dt = timeparse.parse_when(when)
    if dt is None:
        return "Time samajh nahi aaya ('08:30', 'kal 9 baje', 'in 2 hours' jaisa batao)."
    rep = timeparse.normalize_repeat(repeat)
    cur = db.execute("INSERT INTO tasks(name,prompt,spec,next_run,last_run,enabled,created) VALUES(?,?,?,?,?,?,?)",
                     (name.strip() or prompt.strip()[:40], prompt.strip(), rep, dt.timestamp(), 0, 1, time.time()))
    return f"Scheduled task #{cur.lastrowid}: '{prompt.strip()[:60]}' - {timeparse.human(dt)}{', ' + rep if rep else ''}"


@tool(category="schedule", label="List scheduled tasks")
def list_scheduled_tasks() -> str:
    """List all scheduled (recurring or future) Glacier tasks."""
    rows = db.query("SELECT id,name,prompt,spec,next_run FROM tasks WHERE enabled=1 ORDER BY next_run")
    if not rows:
        return "Koi scheduled task nahi hai."
    return "Scheduled tasks:\n" + "\n".join(
        f"#{r['id']} {r['name']} - {timeparse.human(datetime.fromtimestamp(r['next_run']))}"
        f"{' (' + r['spec'] + ')' if r['spec'] else ''}" for r in rows)


@tool(category="schedule", label="Cancel scheduled task")
def cancel_scheduled_task(which: str) -> str:
    """Cancel a scheduled task by number (#id) or words from its name."""
    t = _find(which, "tasks", "name")
    if not t:
        return f"'{which}' naam ka koi scheduled task nahi mila."
    db.execute("DELETE FROM tasks WHERE id=?", (t["id"],))
    return f"Scheduled task cancel kar diya: {t['name']}"
