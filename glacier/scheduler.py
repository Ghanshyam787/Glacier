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
def _fire_reminders(now: float):
    for r in db.query("SELECT * FROM reminders WHERE fired=0 AND fire_at<=?", (now,)):
        late = now - r["fire_at"] > 600
        text = r["text"] if r["text"].lower().startswith(("timer", "reminder")) else f"Reminder: {r['text']}"
        notify.notify(("(late) " if late else "") + text, title="Reminder")
        if r["recur"]:
            nxt = datetime.fromtimestamp(r["fire_at"])
            while nxt.timestamp() <= now:
                nxt = timeparse.next_run(r["recur"], nxt)
            db.execute("UPDATE reminders SET fire_at=? WHERE id=?", (nxt.timestamp(), r["id"]))
        else:
            db.execute("UPDATE reminders SET fired=1 WHERE id=?", (r["id"],))
    db.execute("DELETE FROM reminders WHERE fired=1 AND fire_at < ?", (now - 7 * 86400,))


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
            nxt = datetime.fromtimestamp(t["next_run"])
            while nxt.timestamp() <= now:
                nxt = timeparse.next_run(t["spec"], nxt)
            db.execute("UPDATE tasks SET next_run=?, last_run=? WHERE id=?", (nxt.timestamp(), now, t["id"]))
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
