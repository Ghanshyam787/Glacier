"""
Glacier Tool: Page monitors (OpenJarvis 'monitor' agent jaisa, light version)
Kisi webpage ko har N minute check karo; badle ya keyword aa/jaye to turant notify (bolke + toast + phone).
Examples: result page, price drop, 'in stock', notification board, scholarship page update.
"""

import difflib
import re
import time

import db
import netsafe
import notify
from registry import tool


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


@tool(category="schedule", label="Watch a page")
def watch_page(url: str, keyword: str = "", every_minutes: int = 30) -> str:
    """
    Monitor a web page. With keyword: alert when that word appears or disappears (e.g. 'In stock', 'Result declared').
    Without keyword: alert whenever the page content changes noticeably. Checked every N minutes (min 5) while Glacier runs.
    """
    err = netsafe.ssrf_check(url)
    if err:
        return err
    text, ferr = netsafe.fetch_text(url, max_chars=30000, timeout=15)
    if ferr:
        return f"Page abhi nahi khul raha: {ferr}"
    kw = keyword.strip()
    state = ("yes" if kw.lower() in text.lower() else "no") if kw else _norm(text)[:20000]
    cur = db.execute(
        "INSERT INTO watches(url,keyword,every_min,last_check,last_hash,last_state,enabled,created) VALUES(?,?,?,?,?,?,1,?)",
        (url, kw, max(5, int(every_minutes or 30)), time.time(), "", state, time.time()))
    what = f"'{kw}' aane/jaane par" if kw else "kuchh bhi badalne par"
    now_state = f" (abhi '{kw}' {'page par hai' if state == 'yes' else 'page par nahi hai'})" if kw else ""
    return f"Watch #{cur.lastrowid} shuru: {url} - {what} batata rahunga, har {max(5, int(every_minutes or 30))} min.{now_state}"


@tool(category="schedule", label="List watches")
def list_watches() -> str:
    """List all monitored pages."""
    rows = db.query("SELECT id,url,keyword,every_min FROM watches WHERE enabled=1 ORDER BY id")
    if not rows:
        return "Koi page monitor nahi ho raha."
    return "\n".join(f"#{r['id']} {r['url']}" + (f" [keyword: {r['keyword']}]" if r["keyword"] else " [any change]") +
                     f" every {r['every_min']} min" for r in rows)


@tool(category="schedule", label="Stop watching")
def remove_watch(which: str) -> str:
    """Stop monitoring a page by number (#id) or part of its URL."""
    which = (which or "").strip().lstrip("#")
    row = db.query_one("SELECT * FROM watches WHERE id=?", (int(which),)) if which.isdigit() else \
        db.query_one("SELECT * FROM watches WHERE url LIKE ?", (f"%{which}%",))
    if not row:
        return f"'{which}' ka koi watch nahi mila."
    db.execute("DELETE FROM watches WHERE id=?", (row["id"],))
    return f"Watch hata diya: {row['url']}"


def check_due():
    """Scheduler har tick pe bulata hai. Due watches check karo, badlav par notify."""
    now = time.time()
    for w in db.query("SELECT * FROM watches WHERE enabled=1"):
        if now - w["last_check"] < w["every_min"] * 60:
            continue
        db.execute("UPDATE watches SET last_check=? WHERE id=?", (now, w["id"]))
        text, err = netsafe.fetch_text(w["url"], max_chars=30000, timeout=15)
        if err or not text:
            continue
        if w["keyword"]:
            state = "yes" if w["keyword"].lower() in text.lower() else "no"
            if state != w["last_state"]:
                db.execute("UPDATE watches SET last_state=? WHERE id=?", (state, w["id"]))
                msg = (f"'{w['keyword']}' ab page par aa gaya hai: {w['url']}" if state == "yes"
                       else f"'{w['keyword']}' ab page se hat gaya: {w['url']}")
                notify.notify(msg, title="Page monitor")
        else:
            new = _norm(text)[:20000]
            old = w["last_state"] or ""
            if difflib.SequenceMatcher(None, old[:4000], new[:4000]).quick_ratio() < 0.97 or \
                    difflib.SequenceMatcher(None, old[:4000], new[:4000]).ratio() < 0.97:
                added = [s for s in re.split(r"(?<=[.!?])\s+", new) if s not in old][:2]
                db.execute("UPDATE watches SET last_state=? WHERE id=?", (new, w["id"]))
                snippet = (" Naya: " + " ".join(added)[:160]) if added else ""
                notify.notify(f"Page badal gaya: {w['url']}.{snippet}", title="Page monitor")
