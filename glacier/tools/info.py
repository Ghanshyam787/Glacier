"""
Glacier Tools: Information
date/time, weather (Open-Meteo - free, no key), news (RSS), calculator, unit & currency conversion, dictionary.
"""

import ast
import json
import math
import operator
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import quote_plus

import config
import db
import netsafe
from registry import tool


def _get_json(url: str, timeout: int = 12):
    r, err = netsafe.safe_request("GET", url, timeout=timeout)
    if err:
        raise RuntimeError(err)
    if r.status_code >= 400:
        raise RuntimeError(f"HTTP {r.status_code}")
    return json.loads(netsafe.decode_body(r, netsafe.read_limited(r, 600_000)))


# ---------------------------------------------------------------------------
@tool(category="info", quiet=True, label="Date & time")
def get_datetime(timezone: str = "") -> str:
    """Current date and time. Optional timezone name like 'Asia/Tokyo', 'America/New_York', 'Asia/Seoul'."""
    try:
        if timezone:
            from zoneinfo import ZoneInfo
            now = datetime.now(ZoneInfo(timezone))
            return now.strftime(f"%A, %d %B %Y, %I:%M %p ({timezone})")
    except Exception:
        return f"'{timezone}' timezone samajh nahi aaya (jaise 'Asia/Seoul' likho)."
    return datetime.now().astimezone().strftime("%A, %d %B %Y, %I:%M %p (%Z)")


# ---------------------------------------------------------------------------
_WMO = {0: "saaf aasmaan", 1: "mostly saaf", 2: "thoda badal", 3: "badal chhaye", 45: "kohra", 48: "kohra",
        51: "halki phuhaar", 53: "phuhaar", 55: "tez phuhaar", 61: "halki barish", 63: "barish", 65: "tez barish",
        66: "freezing rain", 67: "freezing rain", 71: "halki barfbaari", 73: "barfbaari", 75: "tez barfbaari",
        77: "snow grains", 80: "barish ke jhonke", 81: "barish ke jhonke", 82: "tez barish ke jhonke",
        85: "snow showers", 86: "snow showers", 95: "aandhi-toofan", 96: "toofan + ole", 99: "toofan + ole"}


def locate(city: str = ""):
    """(lat, lon, label). city blank -> HOME_CITY -> IP location (6 ghante cache)."""
    city = city or config.HOME_CITY
    if city:
        data = _get_json("https://geocoding-api.open-meteo.com/v1/search?count=1&name=" + quote_plus(city))
        res = (data.get("results") or [None])[0]
        if not res:
            raise RuntimeError(f"'{city}' shehar nahi mila.")
        return res["latitude"], res["longitude"], f"{res['name']}, {res.get('admin1', '')}".strip(", ")
    cached = db.kv_get("ip_location")
    if cached:
        c = json.loads(cached)
        if datetime.now().timestamp() - c["t"] < 6 * 3600:
            return c["lat"], c["lon"], c["label"]
    d = _get_json("https://ipwho.is/")
    if not d.get("success", True) or "latitude" not in d:
        raise RuntimeError("Location pata nahi chali - .env mein HOME_CITY daal do.")
    label = f"{d.get('city', '')}, {d.get('region', '')}".strip(", ")
    db.kv_set("ip_location", json.dumps({"t": datetime.now().timestamp(), "lat": d["latitude"], "lon": d["longitude"], "label": label}))
    return d["latitude"], d["longitude"], label


@tool(category="info", untrusted="weather service", label="Weather")
def weather(city: str = "", days: int = 3) -> str:
    """Current weather and the next few days' forecast. Leave city empty for the user's own location."""
    try:
        lat, lon, label = locate(city)
        d = _get_json(
            "https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s&timezone=auto&forecast_days=%d"
            "&current=temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m,precipitation"
            "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
            % (lat, lon, max(1, min(int(days or 3), 7))))
    except Exception as e:
        return f"Weather nahi mila: {e}"
    c, dl = d["current"], d["daily"]
    lines = [f"{label}: abhi {c['temperature_2m']}°C (feels {c['apparent_temperature']}°C), "
             f"{_WMO.get(c['weather_code'], 'mausam')}, humidity {c['relative_humidity_2m']}%, hawa {c['wind_speed_10m']} km/h"]
    for i, day in enumerate(dl["time"]):
        name = "Aaj" if i == 0 else ("Kal" if i == 1 else datetime.fromisoformat(day).strftime("%a %d %b"))
        lines.append(f"{name}: {dl['temperature_2m_min'][i]}-{dl['temperature_2m_max'][i]}°C, "
                     f"{_WMO.get(dl['weather_code'][i], '')}, barish ka chance {dl['precipitation_probability_max'][i]}%")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
def fetch_headlines(topic: str = "", count: int = 6) -> list:
    """[(title, source, date)] - RSS. Raises RuntimeError."""
    feeds = [f"https://news.google.com/rss/search?q={quote_plus(topic)}&hl=en-IN&gl=IN&ceid=IN:en"] if topic \
        else list(config.NEWS_FEEDS)
    items, errs = [], []
    for url in feeds:
        r, err = netsafe.safe_request("GET", url, timeout=12)
        if err:
            errs.append(err)
            continue
        raw = netsafe.read_limited(r, 800_000)
        if b"<!DOCTYPE" in raw[:2000].upper() and b"<!ENTITY" in raw.upper():
            continue  # XML entity attacks
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            continue
        for it in root.iter("item"):
            title = (it.findtext("title") or "").strip()
            src = (it.findtext("source") or "").strip() or root.findtext("./channel/title", "").strip()
            if title:
                items.append((title, src, (it.findtext("pubDate") or "")[:16]))
        if len(items) >= count * 2:
            break
    if not items:
        raise RuntimeError(errs[0] if errs else "News feed khaali aaya")
    seen, out = set(), []
    for t in items:
        k = t[0].lower()[:60]
        if k not in seen:
            seen.add(k)
            out.append(t)
    return out[:count]


@tool(category="info", untrusted="news feeds", label="News")
def news_headlines(topic: str = "", count: int = 6) -> str:
    """Latest news headlines. Give a topic (e.g. 'cricket', 'AI', 'Bihar') or leave empty for top news."""
    try:
        items = fetch_headlines(topic, max(1, min(int(count or 6), 12)))
    except RuntimeError as e:
        return f"News nahi mili: {e}"
    return "Taaza khabrein:\n" + "\n".join(f"- {t} ({s})" if s else f"- {t}" for t, s, _ in items)


# ---------------------------------------------------------------------------
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.USub: operator.neg, ast.UAdd: operator.pos}
_FUNCS = {"sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan, "log": math.log10, "ln": math.log,
          "log10": math.log10, "log2": math.log2, "abs": abs, "round": round, "floor": math.floor, "ceil": math.ceil,
          "factorial": math.factorial, "exp": math.exp, "radians": math.radians, "degrees": math.degrees,
          "asin": math.asin, "acos": math.acos, "atan": math.atan, "min": min, "max": max}
_CONSTS = {"pi": math.pi, "e": math.e}


def _eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp):
        if isinstance(node.op, ast.Pow):
            base, exp = _eval(node.left), _eval(node.right)
            if abs(exp) > 1000 or abs(base) > 1e12:
                raise ValueError("power bahut bada hai")
            return base ** exp
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp):
        return _OPS[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.Name) and node.id in _CONSTS:
        return _CONSTS[node.id]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCS and not node.keywords:
        args = [_eval(a) for a in node.args]
        if node.func.id == "factorial" and args[0] > 500:
            raise ValueError("factorial bahut bada")
        return _FUNCS[node.func.id](*args)
    raise ValueError("expression samajh nahi aaya")


@tool(category="info", quiet=True, label="Calculator")
def calculate(expression: str) -> str:
    """Exactly evaluate a math expression, e.g. '15% of 2400', '(12+8)*3.5', 'sqrt(144)', '2**10'."""
    ex = (expression or "").lower().replace("^", "**").replace("×", "*").replace("÷", "/").replace(",", "")
    ex = re.sub(r"(\d+(?:\.\d+)?)\s*%\s*of\s*", r"(\1/100)*", ex)
    ex = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"(\1/100)", ex)
    try:
        val = _eval(ast.parse(ex.strip(), mode="eval").body)
    except ZeroDivisionError:
        return "Zero se divide nahi ho sakta."
    except Exception as e:
        return f"Calculate nahi ho paya: {e}"
    if isinstance(val, float):
        val = round(val, 10)
        if val == int(val) and abs(val) < 1e15:
            val = int(val)
    return f"{expression.strip()} = {val}"


# ---------------------------------------------------------------------------
_UNITS = {
    "length": {"mm": 0.001, "cm": 0.01, "m": 1, "km": 1000, "in": 0.0254, "inch": 0.0254, "ft": 0.3048, "feet": 0.3048,
               "yd": 0.9144, "mi": 1609.344, "mile": 1609.344, "miles": 1609.344},
    "mass": {"mg": 1e-6, "g": 0.001, "kg": 1, "quintal": 100, "ton": 1000, "tonne": 1000, "oz": 0.0283495,
             "lb": 0.453592, "lbs": 0.453592},
    "volume": {"ml": 0.001, "l": 1, "litre": 1, "liter": 1, "cup": 0.236588, "tsp": 0.00492892, "tbsp": 0.0147868,
               "gal": 3.78541, "gallon": 3.78541},
    "data": {"b": 1, "kb": 1024, "mb": 1024 ** 2, "gb": 1024 ** 3, "tb": 1024 ** 4},
    "speed": {"m/s": 1, "kmh": 0.277778, "km/h": 0.277778, "mph": 0.44704, "knot": 0.514444},
    "area": {"sqm": 1, "m2": 1, "sqft": 0.092903, "acre": 4046.86, "hectare": 10000, "bigha": 2529.29, "katha": 126.45},
    "time": {"s": 1, "sec": 1, "min": 60, "h": 3600, "hour": 3600, "day": 86400, "week": 604800},
}


@tool(category="info", quiet=True, label="Unit convert")
def convert_units(value: float, from_unit: str, to_unit: str) -> str:
    """Convert between units: length, weight, volume, data size, speed, area (incl. bigha/katha), time, temperature (c/f/k)."""
    a, b = from_unit.lower().strip(), to_unit.lower().strip()
    temps = {"c", "f", "k", "celsius", "fahrenheit", "kelvin"}
    if a in temps and b in temps:
        a, b = a[0], b[0]
        c = value if a == "c" else (value - 32) * 5 / 9 if a == "f" else value - 273.15
        out = c if b == "c" else c * 9 / 5 + 32 if b == "f" else c + 273.15
        return f"{value} °{a.upper()} = {out:.2f} °{b.upper()}"
    for table in _UNITS.values():
        if a in table and b in table:
            return f"{value} {from_unit} = {value * table[a] / table[b]:.6g} {to_unit}"
    return "In units ka conversion nahi aata (dono same category ke hone chahiye)."


@tool(category="info", untrusted="currency service", label="Currency")
def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    """Convert money using live exchange rates, e.g. 100 USD to INR, 50000 KRW to INR."""
    a, b = from_currency.upper().strip(), to_currency.upper().strip()
    try:
        d = _get_json(f"https://open.er-api.com/v6/latest/{quote_plus(a)}")
        rate = d["rates"][b]
    except Exception as e:
        return f"Rate nahi mila: {e}"
    return f"{amount:,.2f} {a} = {amount * rate:,.2f} {b} (1 {a} = {rate:.4f} {b})"


@tool(category="info", untrusted="dictionary", label="Dictionary")
def define_word(word: str) -> str:
    """English dictionary meaning, part of speech and an example for a word."""
    try:
        d = _get_json("https://api.dictionaryapi.dev/api/v2/entries/en/" + quote_plus(word.strip().lower()))
        lines = []
        for m in d[0]["meanings"][:3]:
            df = m["definitions"][0]
            ex = f' (e.g. "{df["example"]}")' if df.get("example") else ""
            lines.append(f"{m['partOfSpeech']}: {df['definition']}{ex}")
        return f"{word}: " + " | ".join(lines)
    except Exception:
        return f"'{word}' ka meaning nahi mila."
