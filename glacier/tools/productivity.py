"""
Glacier Tools: Productivity (local & private)
To-do list, notes, calendar, contacts - sab SQLite mein, tumhare PC par. (Google Calendar jaisa cloud sync nahi.)
"""

import time
from datetime import datetime, timedelta

import db
import timeparse
from registry import tool

# ------------------------------------------------------------------ todos


@tool(category="productivity", label="Add to-do")
def add_todo(text: str, due: str = "") -> str:
    """Add an item to the to-do list. 'due' is optional and natural (e.g. 'kal', 'friday 5pm')."""
    due_dt = timeparse.parse_when(due) if due else None
    cur = db.execute("INSERT INTO todos(text,done,due,created) VALUES(?,?,?,?)",
                     (text.strip(), 0, due_dt.strftime("%Y-%m-%d %H:%M") if due_dt else "", time.time()))
    return f"To-do #{cur.lastrowid} add: {text.strip()}" + (f" (due {timeparse.human(due_dt)})" if due_dt else "")


@tool(category="productivity", label="List to-dos")
def list_todos(show_done: bool = False) -> str:
    """Show the to-do list (pending items; set show_done=True to include completed)."""
    rows = db.query("SELECT id,text,done,due FROM todos " + ("" if show_done else "WHERE done=0 ") + "ORDER BY done, id")
    if not rows:
        return "To-do list khaali hai."
    return "\n".join(f"#{r['id']} [{'x' if r['done'] else ' '}] {r['text']}" + (f" (due {r['due']})" if r['due'] else "")
                     for r in rows)


@tool(category="productivity", label="Complete to-do")
def complete_todo(which: str) -> str:
    """Mark a to-do as done, by number (#id) or words from its text."""
    which = (which or "").strip().lstrip("#")
    row = db.query_one("SELECT * FROM todos WHERE id=?", (int(which),)) if which.isdigit() else \
        db.query_one("SELECT * FROM todos WHERE done=0 AND text LIKE ? ORDER BY id DESC", (f"%{which}%",))
    if not row:
        return f"'{which}' naam ka pending to-do nahi mila."
    db.execute("UPDATE todos SET done=1, completed=? WHERE id=?", (time.time(), row["id"]))
    return f"Done: {row['text']}"


@tool(category="productivity", label="Delete to-do")
def delete_todo(which: str) -> str:
    """Remove a to-do entirely, by number (#id) or words from its text."""
    which = (which or "").strip().lstrip("#")
    row = db.query_one("SELECT * FROM todos WHERE id=?", (int(which),)) if which.isdigit() else \
        db.query_one("SELECT * FROM todos WHERE text LIKE ? ORDER BY id DESC", (f"%{which}%",))
    if not row:
        return f"'{which}' naam ka to-do nahi mila."
    db.execute("DELETE FROM todos WHERE id=?", (row["id"],))
    return f"To-do hata diya: {row['text']}"


# ------------------------------------------------------------------ notes
@tool(category="productivity", label="Save note")
def add_note(text: str, title: str = "") -> str:
    """Save a note (ideas, meeting points, anything to remember in detail). Use remember() for short personal facts."""
    title = title.strip() or text.strip().split("\n")[0][:50]
    cur = db.execute("INSERT INTO notes(title,body,created) VALUES(?,?,?)", (title, text.strip(), time.time()))
    return f"Note #{cur.lastrowid} save: {title}"


@tool(category="productivity", untrusted="your notes", label="Search notes")
def search_notes(query: str = "", limit: int = 8) -> str:
    """Search saved notes by words (empty query = latest notes)."""
    if query.strip():
        like = f"%{query.strip()}%"
        rows = db.query("SELECT id,title,body,created FROM notes WHERE title LIKE ? OR body LIKE ? ORDER BY id DESC LIMIT ?",
                        (like, like, limit))
    else:
        rows = db.query("SELECT id,title,body,created FROM notes ORDER BY id DESC LIMIT ?", (limit,))
    if not rows:
        return "Koi note nahi mila."
    return "\n".join(f"#{r['id']} {r['title']} ({datetime.fromtimestamp(r['created']):%d %b}): {r['body'][:200]}" for r in rows)


@tool(category="productivity", label="Delete note")
def delete_note(which: str) -> str:
    """Delete a note by number (#id)."""
    which = (which or "").strip().lstrip("#")
    if not which.isdigit():
        return "Note ka number batao (jaise 3)."
    cur = db.execute("DELETE FROM notes WHERE id=?", (int(which),))
    return "Note delete kar diya." if cur.rowcount else "Is number ka note nahi mila."


# ------------------------------------------------------------------ calendar
@tool(category="productivity", label="Add calendar event")
def add_event(title: str, when: str, duration_minutes: int = 60, notes: str = "") -> str:
    """Add an event to the local calendar. 'when' is natural: 'kal 4pm', 'friday 10:30', '2026-11-02 09:00'. Glacier reminds 10 minutes before."""
    dt = timeparse.parse_when(when)
    if dt is None:
        return "Time samajh nahi aaya ('kal 4pm', 'friday 10:30' jaisa batao)."
    end = dt + timedelta(minutes=max(5, int(duration_minutes or 60)))
    cur = db.execute("INSERT INTO calendar_events(title,start,end,notes,reminded) VALUES(?,?,?,?,0)",
                     (title.strip(), dt.timestamp(), end.timestamp(), notes))
    return f"Event #{cur.lastrowid}: '{title.strip()}' - {timeparse.human(dt)}"


def events_between(start_ts: float, end_ts: float) -> list:
    return db.query("SELECT id,title,start,end,notes FROM calendar_events WHERE start>=? AND start<? ORDER BY start",
                    (start_ts, end_ts))


@tool(category="productivity", label="List calendar")
def list_events(days: int = 7) -> str:
    """Show calendar events for the next N days (default 7; use 1 for today)."""
    now = datetime.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    rows = events_between(start.timestamp(), (start + timedelta(days=max(1, int(days or 7)))).timestamp())
    if not rows:
        return "In dino mein koi event nahi hai."
    return "\n".join(f"#{r['id']} {timeparse.human(datetime.fromtimestamp(r['start']), now)} - {r['title']}" for r in rows)


@tool(category="productivity", label="Delete event")
def delete_event(which: str) -> str:
    """Delete a calendar event by number (#id) or words from its title."""
    which = (which or "").strip().lstrip("#")
    row = db.query_one("SELECT * FROM calendar_events WHERE id=?", (int(which),)) if which.isdigit() else \
        db.query_one("SELECT * FROM calendar_events WHERE title LIKE ? ORDER BY start DESC", (f"%{which}%",))
    if not row:
        return f"'{which}' naam ka event nahi mila."
    db.execute("DELETE FROM calendar_events WHERE id=?", (row["id"],))
    return f"Event delete: {row['title']}"


# ------------------------------------------------------------------ contacts
@tool(category="productivity", label="Save contact")
def add_contact(name: str, phone: str = "", email: str = "", notes: str = "") -> str:
    """Save or update a contact (used by send_whatsapp / send_email so you can say 'Papa ko message bhejo')."""
    existing = db.query_one("SELECT id FROM contacts WHERE name LIKE ?", (name.strip(),))
    if existing:
        db.execute("UPDATE contacts SET phone=COALESCE(NULLIF(?,''),phone), email=COALESCE(NULLIF(?,''),email), "
                   "notes=COALESCE(NULLIF(?,''),notes) WHERE id=?", (phone, email, notes, existing["id"]))
        return f"Contact update: {name.strip()}"
    db.execute("INSERT INTO contacts(name,phone,email,notes) VALUES(?,?,?,?)", (name.strip(), phone.strip(), email.strip(), notes))
    return f"Contact save: {name.strip()}"


def lookup_contact(name: str):
    return db.query_one("SELECT * FROM contacts WHERE name LIKE ? ORDER BY (name = ?) DESC LIMIT 1",
                        (f"%{name.strip()}%", name.strip()))


@tool(category="productivity", label="Find contact")
def find_contact(name: str = "") -> str:
    """Find a saved contact by name (empty = list all)."""
    rows = db.query("SELECT name,phone,email FROM contacts WHERE name LIKE ? ORDER BY name", (f"%{name.strip()}%",))
    if not rows:
        return "Koi contact nahi mila."
    return "\n".join(f"{r['name']}: {r['phone'] or '-'} | {r['email'] or '-'}" for r in rows)
