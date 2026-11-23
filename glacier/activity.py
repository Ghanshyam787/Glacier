"""
Glacier - Activity log (dashboard ke 'Recent activity' panel ke liye).
Sirf tab likhta hai jab koi tool ACTUALLY chala ho. Database mein persist hota hai,
isliye restart ke baad bhi dikhta hai.
"""

import time
from datetime import datetime

import db
import events

MAX_KEEP = 2000


def add_activity(text: str, label: str = ""):
    if not text:
        return
    try:
        db.execute("INSERT INTO activity(ts,label,text) VALUES(?,?,?)", (time.time(), label, text[:160]))
        db.execute(
            "DELETE FROM activity WHERE id <= (SELECT MAX(id) FROM activity) - ?", (MAX_KEEP,)
        )
        events.publish("activity", label=label, text=text[:160])
    except Exception:
        pass


def get_activity(limit: int = 10) -> list:
    try:
        rows = db.query("SELECT ts,label,text FROM activity ORDER BY id DESC LIMIT ?", (limit,))
    except Exception:
        return []
    return [{"time": datetime.fromtimestamp(r["ts"]).strftime("%H:%M"), "text": r["text"]} for r in rows]


def get_activity_full(limit: int = 300) -> list:
    """'View all' ke liye: date ke saath poori history."""
    try:
        rows = db.query("SELECT ts,label,text FROM activity ORDER BY id DESC LIMIT ?", (max(1, min(int(limit), 2000)),))
    except Exception:
        return []
    now = datetime.now()
    out = []
    for r in rows:
        d = datetime.fromtimestamp(r["ts"])
        day = "Aaj" if d.date() == now.date() else d.strftime("%d %b")
        out.append({"time": d.strftime("%H:%M"), "day": day, "label": r["label"] or "", "text": r["text"]})
    return out
