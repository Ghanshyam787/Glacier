"""
Glacier - Scheduler & proactive engine (OpenJarvis ke 'scheduled agents' + 'proactive' jaisa)
Ek background thread har 15 second mein:
  * reminders / timers fire karta hai (late bhi - agar PC band tha)
  * scheduled tasks chalata hai (Glacier khud prompt chalata hai aur natija bolta hai)
  * calendar events se 10 minute pehle yaad dilata hai
  * page monitors check karta hai
  * roz subah morning digest
  * proactive alerts: battery low, disk full, CPU/RAM atka hua
Kuchh bhi crash karta hai to sirf log hota hai, thread chalta rehta hai.
"""

import threading
import time
from datetime import datetime

import config
import db
import notify
import registry
import timeparse

TICK_SECONDS = 15
_started = False
_state = {"battery_alerted": False, "disk_day": "", "hot_ticks": 0, "last_hot_alert": 0.0}


# ------------------------------------------------------------------ reminders
GRACE_SECONDS = max(1, config.MISSED_GRACE_MINUTES) * 60   # itna late ho to normal tarah fire; isse zyada late = purana (chup)
GAP_SECONDS = 180         # do ticks ke beech itna gap = PC band/sleep tha -> catch-up


def _advance(recur: str, fire_at: float, now: float):
    """Repeat wale item ka agla FUTURE time aur beech mein kitne occurrence chhoote: (next_ts, missed_count)."""
    if recur.startswith("every:"):
        step = max(60, int(recur.split(":")[1]) * 60)
        missed = int((now - fire_at) // step) + 1
        return fire_at + missed * step, missed
    nxt, missed = datetime.fromtimestamp(fire_at), 0
    while nxt.timestamp() <= now and missed < 5000:
        nxt = timeparse.next_run(recur, nxt)
        missed += 1
    return nxt.timestamp(), missed


def _ago(seconds: float) -> str:
    m = int(seconds // 60)
    if m < 60:
        return f"{max(m, 1)} minute"
    h = m // 60
    if h < 48:
        return f"{h} ghante" + (f" {m % 60} minute" if m % 60 and h < 6 else "")
    return f"{h // 24} din"


def _when(ts: float, now: float) -> str:
    d, n = datetime.fromtimestamp(ts), datetime.fromtimestamp(now)
    clock = d.strftime("%I:%M %p").lstrip("0")
    if d.date() == n.date():
        return f"aaj {clock}"
    if (n.date() - d.date()).days == 1:
        return f"kal {clock}"
    return d.strftime("%d %b ") + clock


def _label(text: str) -> str:
    t = text or ""
    if t.lower().startswith("timer"):
        return "Timer: " + (t.split(":", 1)[1].strip() if ":" in t else "khatam")
    return t


def _catch_up(now: float, last_alive: float):
    """PC band/sleep ke baad: asli abhi ka time dekhkar, jo kuchh chhoota use EK baar mein batao (har ek alag-alag nahi bolna)."""
    gap = now - last_alive
    lines = []
    for r in db.query("SELECT * FROM reminders WHERE fired=0 AND fire_at<? ORDER BY fire_at", (now - GRACE_SECONDS,)):
        if r["recur"]:
            nxt, missed = _advance(r["recur"], r["fire_at"], now)
            db.execute("UPDATE reminders SET fire_at=? WHERE id=?", (nxt, r["id"]))
            lines.append(f"{_label(r['text'])} ({missed} baar chhoota, ab agla {_when(nxt, now)})")
        else:
            db.execute("UPDATE reminders SET fired=1, status='missed', done_at=? WHERE id=?", (now, r["id"]))
            lines.append(f"{_label(r['text'])} ({_when(r['fire_at'], now)} ka tha)")
    for t in db.query("SELECT * FROM tasks WHERE enabled=1 AND next_run<? ORDER BY next_run", (now - GRACE_SECONDS,)):
        if t["spec"]:
            nxt, missed = _advance(t["spec"], t["next_run"], now)
            db.execute("UPDATE tasks SET next_run=? WHERE id=?", (nxt, t["id"]))
            lines.append(f"Scheduled task '{t['name']}' ({missed} baar chhoota, agla {_when(nxt, now)})")
        else:
            db.execute("UPDATE tasks SET enabled=0 WHERE id=?", (t["id"],))
            lines.append(f"Scheduled task '{t['name']}' ({_when(t['next_run'], now)} ka tha)")
    for e in db.query("SELECT * FROM calendar_events WHERE reminded=0 AND start<? AND start>?", (now - 300, last_alive - 3600)):
        db.execute("UPDATE calendar_events SET reminded=1 WHERE id=?", (e["id"],))
        lines.append(f"Event '{e['title']}' ({_when(e['start'], now)})")
    if not config.ANNOUNCE_MISSED:
        # Default: purane reminder BOLO MAT. Wo "Chhoote" filter mein rehte hain (View all), repeat wale agle sahi time par chale gaye.
        if lines:
            try:
                import activity
                activity.add_activity(f"{len(lines)} purane reminder/task chhoote (PC band: {_ago(gap)})", "reminder")
            except Exception:
                pass
        return
    off = datetime.fromtimestamp(last_alive).strftime("%d %b, %I:%M %p").replace(" 0", " ")
    head = f"Welcome back {config.USER_ADDRESS}. Glacier {_ago(gap)} se band tha (last {off} se)."
    if not lines:
        notify.notify(head + " Is beech koi reminder nahi chhoota.", title="Welcome back")
        return
    shown = lines[:6]
    more = f" Aur {len(lines) - 6} chhoote." if len(lines) > 6 else ""
    body = f" Is beech {len(lines)} cheez chhoot gayi: " + "; ".join(shown) + "." + more
    notify.notify(head + body + " Poori list Reminders > View all mein hai, wahan se dobara set kar sakte ho.", title="Welcome back")
    try:
        import activity
        activity.add_activity(f"{len(lines)} reminder/task chhoote (PC band: {_ago(gap)})", "reminder")
    except Exception:
        pass


def _fire_reminders(now: float):
    for r in db.query("SELECT * FROM reminders WHERE fired=0 AND fire_at<=?", (now,)):
        late = now - r["fire_at"]
        text = r["text"] if r["text"].lower().startswith(("timer", "reminder")) else f"Reminder: {r['text']}"
        if late > 120:
            text += f" (ye {_ago(late)} pehle ka tha)"
        notify.notify(text, title="Reminder")
        if r["recur"]:
            nxt, _missed = _advance(r["recur"], r["fire_at"], now)
            db.execute("UPDATE reminders SET fire_at=? WHERE id=?", (nxt, r["id"]))
        else:
            db.execute("UPDATE reminders SET fired=1, status='fired', done_at=? WHERE id=?", (now, r["id"]))
    # NOTE: purane reminders ab delete nahi hote - poori history Reminders panel mein rehti hai.


def _heartbeat_and_gap(now: float):
    """Pichli baar kab zinda tha dekho; bada gap ho to catch-up. Phir heartbeat likho."""
    try:
        last = float(db.kv_get("last_alive", "0") or 0)
    except ValueError:
        last = 0.0
    try:
        if last and now - last > GAP_SECONDS:
            _catch_up(now, last)
    finally:
        db.kv_set("last_alive", str(now))


# ------------------------------------------------------------------ scheduled agent tasks
def _run_task(task_id: int, name: str, prompt: str):
    try:
        import brain
        reply = brain.ask_glacier(prompt, session="scheduler", ephemeral=True)
        notify.notify(f"{name}: {reply}" if len(reply) < 400 else reply, title=f"Scheduled: {name}"[:40])
    except Exception as e:
        registry.log_error(f"scheduled task {task_id}", e)


def _fire_tasks(now: float):
    for t in db.query("SELECT * FROM tasks WHERE enabled=1 AND next_run<=?", (now,)):
        if t["spec"]:
            nxt, _missed = _advance(t["spec"], t["next_run"], now)
            db.execute("UPDATE tasks SET next_run=?, last_run=? WHERE id=?", (nxt, now, t["id"]))
        else:
            db.execute("UPDATE tasks SET enabled=0, last_run=? WHERE id=?", (now, t["id"]))
        threading.Thread(target=_run_task, args=(t["id"], t["name"], t["prompt"]), daemon=True).start()


# ------------------------------------------------------------------ calendar heads-up
def _calendar_alerts(now: float):
    for e in db.query("SELECT * FROM calendar_events WHERE reminded=0 AND start BETWEEN ? AND ?", (now - 300, now + 600)):
        mins = max(0, int((e["start"] - now) / 60))
        notify.notify(f"Event: {e['title']} - {('%d minute mein' % mins) if mins else 'abhi'} shuru hoga.", title="Calendar")
        db.execute("UPDATE calendar_events SET reminded=1 WHERE id=?", (e["id"],))


# ------------------------------------------------------------------ digest
def _maybe_digest(now_dt: datetime):
    if not config.DIGEST_ENABLED:
        return
    today = now_dt.strftime("%Y-%m-%d")
    if db.kv_get("digest_last_date") == today:
        return
    try:
        hh, mm = map(int, config.DIGEST_TIME.split(":"))
    except ValueError:
        hh, mm = 8, 0
    due = now_dt >= now_dt.replace(hour=hh, minute=mm, second=0, microsecond=0) or \
        (config.DIGEST_ON_FIRST_START and 5 <= now_dt.hour < 12)
    if not due or now_dt.hour >= 22:
        return
    db.kv_set("digest_last_date", today)  # pehle mark: dobara ya parallel na chale

    def go():
        try:
            from tools.digest import build_digest
            notify.notify(build_digest(), title="Good morning")
        except Exception as e:
            registry.log_error("digest", e)
    threading.Thread(target=go, daemon=True).start()


# ------------------------------------------------------------------ proactive alerts
def _proactive(now: float):
    if not config.PROACTIVE_ALERTS:
        return
    try:
        import psutil
    except ImportError:
        return
    try:
        b = psutil.sensors_battery()
    except Exception:
        b = None
    if b:
        if not b.power_plugged and b.percent <= config.BATTERY_LOW_PERCENT and not _state["battery_alerted"]:
            _state["battery_alerted"] = True
            notify.notify(f"Battery sirf {b.percent:.0f}% bachi hai. Charger laga lo.", title="Battery low")
        elif b.power_plugged or b.percent > config.BATTERY_LOW_PERCENT + 10:
            _state["battery_alerted"] = False
    day = datetime.now().strftime("%Y-%m-%d")
    if _state["disk_day"] != day:
        try:
            part = "C:\\" if config.IS_WINDOWS else "/"
            u = psutil.disk_usage(part)
            if u.percent >= 92:
                _state["disk_day"] = day
                notify.notify(f"{part} drive {u.percent:.0f}% bhar gaya hai, sirf {u.free / 1024**3:.0f} GB free. "
                              "Bolo to bade files dhundh ke safai kar dun.", title="Disk full")
            else:
                _state["disk_day"] = day
        except Exception:
            pass
    cpu, ram = psutil.cpu_percent(interval=None), psutil.virtual_memory().percent
    if cpu > 92 or ram > 93:
        _state["hot_ticks"] += 1
    else:
        _state["hot_ticks"] = 0
    if _state["hot_ticks"] >= 5 and now - _state["last_hot_alert"] > 1800:
        _state["last_hot_alert"] = now
        _state["hot_ticks"] = 0
        top = ""
        try:
            procs = sorted(psutil.process_iter(["name", "memory_percent"]), key=lambda p: -(p.info["memory_percent"] or 0))
            top = f" Sabse zyada: {procs[0].info['name']}." if procs else ""
        except Exception:
            pass
        notify.notify(f"PC kaafi der se atka hua hai (CPU {cpu:.0f}%, RAM {ram:.0f}%).{top}", title="PC slow")


# ------------------------------------------------------------------ main loop
def _tick():
    now = time.time()
    steps = (
        lambda: _heartbeat_and_gap(now),
        lambda: _fire_reminders(now), lambda: _fire_tasks(now), lambda: _calendar_alerts(now),
        lambda: _maybe_digest(datetime.now()), lambda: _proactive(now),
    )
    for step in steps:
        try:
            step()
        except Exception as e:
            registry.log_error("scheduler step", e)
    try:
        from tools import monitors
        monitors.check_due()
    except Exception as e:
        registry.log_error("monitors", e)


def start():
    global _started
    if _started:
        return
    _started = True

    def loop():
        time.sleep(5)
        try:
            import psutil
            psutil.cpu_percent(interval=None)
        except Exception:
            pass
        while True:
            _tick()
            time.sleep(TICK_SECONDS)

    threading.Thread(target=loop, daemon=True, name="glacier-scheduler").start()
