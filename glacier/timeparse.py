"""
Glacier - natural time parsing (English + Hinglish)
parse_when("in 10 minutes") / ("kal 9 baje") / ("tomorrow 7pm") / ("monday 5:30 pm") / ("2026-10-20 15:00")
parse_duration("1h30m") / ("10 minute") / ("90 sec")
next_run(repeat, base) - repeat: daily | weekdays | weekly | every:N (minutes)
"""

import re
from datetime import datetime, timedelta

_WEEKDAYS = {
    "monday": 0, "mon": 0, "somvar": 0, "tuesday": 1, "tue": 1, "tues": 1, "mangalvar": 1,
    "wednesday": 2, "wed": 2, "budhvar": 2, "thursday": 3, "thu": 3, "thurs": 3, "guruvar": 3, "veervar": 3,
    "friday": 4, "fri": 4, "shukravar": 4, "saturday": 5, "sat": 5, "shanivar": 5, "sunday": 6, "sun": 6,
    "ravivar": 6, "itwar": 6,
}
_MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}

_UNIT_SECONDS = {
    "s": 1, "sec": 1, "secs": 1, "second": 1, "seconds": 1, "sekund": 1,
    "m": 60, "min": 60, "mins": 60, "minute": 60, "minutes": 60, "minat": 60,
    "h": 3600, "hr": 3600, "hrs": 3600, "hour": 3600, "hours": 3600, "ghanta": 3600, "ghante": 3600, "ghanta.": 3600,
    "d": 86400, "day": 86400, "days": 86400, "din": 86400,
}
_DUR_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(seconds?|secs?|sekund|s|minutes?|mins?|minat|m|hours?|hrs?|hr|h|ghante|ghanta|days?|din|d)\b")


def parse_duration(text: str):
    """Seconds (float) ya None."""
    t = (text or "").lower()
    total, found = 0.0, False
    for num, unit in _DUR_RE.findall(t):
        total += float(num) * _UNIT_SECONDS[unit]
        found = True
    if not found and re.fullmatch(r"\s*\d+(\.\d+)?\s*", t):
        return float(t) * 60  # bare number = minutes
    if "aadha ghanta" in t or "half hour" in t or "half an hour" in t:
        return 1800.0
    return total if found else None


def _clock(text: str):
    """(hour, minute, matched) - '7pm', '7:30 am', '19:00', '9 baje', 'subah 8', 'shaam 6 baje'."""
    t = text.lower()
    m = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)", t)
    if m:
        h, mi, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3)[0]
        if h == 12:
            h = 0
        if ap == "p":
            h += 12
        return h % 24, mi, True
    m = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", t)
    if m:
        return int(m.group(1)), int(m.group(2)), True
    m = re.search(r"\b(\d{1,2})\s*(?:baje|bje|o'?clock)", t)
    if m:
        h = int(m.group(1)) % 24
        if re.search(r"\b(shaam|sham|raat|dopahar|evening|night|afternoon)\b", t) and h < 12:
            h += 12
        return h, 0, True
    m = re.search(r"\b(subah|shaam|sham|raat|dopahar|morning|evening|night|afternoon)\s+(\d{1,2})\b", t)
    if m:
        h = int(m.group(2)) % 24
        if m.group(1) in ("shaam", "sham", "raat", "dopahar", "evening", "night", "afternoon") and h < 12:
            h += 12
        return h, 0, True
    return None, None, False


def parse_when(text: str, now: datetime = None):
    """datetime ya None. Time-only aur nikal chuka ho to agla din."""
    now = now or datetime.now()
    t = (text or "").strip().lower()
    if not t:
        return None

    # ISO / explicit date
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})(?:[ t](\d{1,2}):(\d{2}))?", t)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        h, mi = (int(m.group(4)), int(m.group(5))) if m.group(4) else (9, 0)
        try:
            return datetime(y, mo, d, h, mi)
        except ValueError:
            return None

    # relative: "in 10 minutes", "10 minute baad", "after 2 hours"
    if re.search(r"\b(in|after|baad|later|mein)\b", t) or t.startswith("+"):
        secs = parse_duration(t)
        if secs:
            return now + timedelta(seconds=secs)
    if re.fullmatch(r"\s*(\d+(?:\.\d+)?\s*(?:seconds?|secs?|minutes?|mins?|hours?|hrs?|ghante|ghanta|din|days?|[smhd]))+\s*", t):
        secs = parse_duration(t)
        if secs:
            return now + timedelta(seconds=secs)

    day = None
    if re.search(r"\b(parso|day after tomorrow)\b", t):
        day = now.date() + timedelta(days=2)
    elif re.search(r"\b(kal|tomorrow|tmrw|tmr)\b", t):
        day = now.date() + timedelta(days=1)
    elif re.search(r"\b(aaj|today|tonight|tonite)\b", t):
        day = now.date()

    if day is None:
        for name, wd in _WEEKDAYS.items():
            if re.search(rf"\b{name}\b", t):
                delta = (wd - now.weekday()) % 7
                if delta == 0 and ("next" in t or "agle" in t):
                    delta = 7
                day = now.date() + timedelta(days=delta)
                break

    if day is None:
        m = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b", t)
        if m:
            d, mo = int(m.group(1)), _MONTHS[m.group(2)]
            y = now.year
            try:
                cand = datetime(y, mo, d).date()
                if cand < now.date():
                    cand = datetime(y + 1, mo, d).date()
                day = cand
            except ValueError:
                return None
        else:
            m = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b(?!:)", t)
            if m and not re.search(r"\d:\d", m.group(0)):
                d, mo = int(m.group(1)), int(m.group(2))
                y = int(m.group(3)) if m.group(3) else now.year
                if y < 100:
                    y += 2000
                try:
                    day = datetime(y, mo, d).date()
                except ValueError:
                    return None

    h, mi, has_clock = _clock(t)
    if "subah" in t and not has_clock and "morning" not in t:
        pass
    if has_clock:
        base_day = day or now.date()
        dt = datetime(base_day.year, base_day.month, base_day.day, h, mi)
        if day is None and dt <= now:
            dt += timedelta(days=1)
        return dt
    if day is not None:
        return datetime(day.year, day.month, day.day, 9, 0) if day != now.date() else None
    return None


def normalize_repeat(text: str) -> str:
    t = (text or "").strip().lower()
    if not t or t in ("no", "none", "once", "nahi"):
        return ""
    if re.search(r"\b(weekday|weekdays|mon-fri|monday to friday)\b", t):
        return "weekdays"
    if re.search(r"\b(week|weekly|har hafte|hafte)\b", t) and not re.search(r"every\s+\d", t):
        return "weekly"
    m = re.search(r"every\s+(\d+)\s*(minutes?|mins?|hours?|hrs?|h|m)\b", t) or \
        re.search(r"har\s+(\d+)\s*(minute|min|ghante|ghanta|hour)", t)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        mins = n * 60 if unit.startswith(("h", "g")) else n
        return f"every:{max(1, mins)}"
    if re.search(r"\b(daily|everyday|every day|roz|har din|rozana)\b", t):
        return "daily"
    return ""


def next_run(repeat: str, base: datetime) -> datetime:
    """Agla occurrence (base ke baad)."""
    if repeat == "daily":
        return base + timedelta(days=1)
    if repeat == "weekly":
        return base + timedelta(days=7)
    if repeat == "weekdays":
        nxt = base + timedelta(days=1)
        while nxt.weekday() >= 5:
            nxt += timedelta(days=1)
        return nxt
    if repeat.startswith("every:"):
        return base + timedelta(minutes=int(repeat.split(":")[1]))
    return base


def human(dt: datetime, now: datetime = None) -> str:
    now = now or datetime.now()
    if dt.date() == now.date():
        return dt.strftime("%I:%M %p").lstrip("0")
    if dt.date() == (now + timedelta(days=1)).date():
        return "kal " + dt.strftime("%I:%M %p").lstrip("0")
    return dt.strftime("%a %d %b, %I:%M %p").replace(" 0", " ")
