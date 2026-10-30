"""
Glacier - Configuration
========================
Saari settings yahin se aati hain. Tumhe is file ko EDIT karne ki zaroorat nahi hai.
Apni settings `.env` file mein daalo (install.bat ye file khud bana deta hai,
`.env.example` se copy hoti hai). Real environment variables `.env` se upar rehte hain.

Sabse zaroori: GEMINI_API_KEY  (free key: https://aistudio.google.com/apikey)
"""

import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


# --------------------------------------------------------------------------
# .env loader (no extra dependency)
# --------------------------------------------------------------------------
def _load_dotenv(path: str):
    try:
        with open(path, encoding="utf-8-sig") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key, value = key.strip(), value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                else:
                    value = re.split(r"\s+#", value, maxsplit=1)[0].strip()
                if key and key not in os.environ:
                    os.environ[key] = value
    except OSError:
        pass


_load_dotenv(os.path.join(BASE_DIR, ".env"))


def _str(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _bool(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    if v is None or v.strip() == "":
        return default
    return v.strip().lower() in ("1", "true", "yes", "on", "y", "haan")


def _int(name: str, default: int) -> int:
    try:
        return int(_str(name, str(default)))
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(_str(name, str(default)))
    except ValueError:
        return default


def _list(name: str, default=None, sep=",") -> list:
    raw = _str(name, "")
    if not raw:
        return list(default or [])
    return [p.strip() for p in raw.split(sep) if p.strip()]


IS_WINDOWS = os.name == "nt"

# --------------------------------------------------------------------------
# Identity
# --------------------------------------------------------------------------
ASSISTANT_NAME = _str("ASSISTANT_NAME", "Glacier")
USER_NAME = _str("USER_NAME", "Shyam")                     # Glacier isi naam se bulayega
USER_ADDRESS = _str("USER_ADDRESS", "Shyam sir")           # kaise sambodhit kare ("Shyam sir" / "Sir")

# --------------------------------------------------------------------------
# Data folder (database, logs, indexes, browser profile) - all local
# --------------------------------------------------------------------------
DATA_DIR = _str("GLACIER_DATA_DIR", os.path.join(BASE_DIR, "data"))
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "glacier.db")
AUDIT_LOG = os.path.join(DATA_DIR, "audit.log")
ERROR_LOG = os.path.join(DATA_DIR, "errors.log")
SKILLS_DIR = os.path.join(BASE_DIR, "skills")
REPORTS_DIRNAME = "Glacier Reports"

# --------------------------------------------------------------------------
# LLM engines
# --------------------------------------------------------------------------
GEMINI_API_KEY = _str("GEMINI_API_KEY") or _str("GLACIER_API_KEY")

# Preferred model first. Free-tier note: "Flash-Lite" models get ~500 requests/day,
# normal "Flash" only ~20/day. Glacier auto-discovers other available models and
# falls back to them when one runs out of quota.
MODEL_NAME = _str("MODEL_NAME", "gemini-3.5-flash-lite")
MODEL_FALLBACKS = _list("MODEL_FALLBACKS", ["gemini-3.6-flash-lite", "gemini-2.5-flash-lite", "gemini-3.6-flash"])
AUTO_DISCOVER_MODELS = _bool("AUTO_DISCOVER_MODELS", True)
DAILY_REQUEST_LIMIT = _int("DAILY_REQUEST_LIMIT", 500)   # only used for the quota meter
MAX_HISTORY_ENTRIES = _int("MAX_HISTORY_ENTRIES", 40)    # chat history kept in memory

# Optional offline / second-opinion engine: any OpenAI-compatible server.
#   Ollama   : OPENAI_COMPAT_BASE_URL=http://localhost:11434/v1   OPENAI_COMPAT_MODEL=llama3.2
#   Groq     : OPENAI_COMPAT_BASE_URL=https://api.groq.com/openai/v1  (free tier key)
#   OpenRouter: OPENAI_COMPAT_BASE_URL=https://openrouter.ai/api/v1
OPENAI_COMPAT_BASE_URL = _str("OPENAI_COMPAT_BASE_URL")
OPENAI_COMPAT_MODEL = _str("OPENAI_COMPAT_MODEL", "llama3.2")
OPENAI_COMPAT_API_KEY = _str("OPENAI_COMPAT_API_KEY", "ollama")
AUTO_DETECT_OLLAMA = _bool("AUTO_DETECT_OLLAMA", True)


def has_api_key() -> bool:
    k = GEMINI_API_KEY
    return bool(k) and not k.upper().startswith("PASTE") and len(k) >= 20


# --------------------------------------------------------------------------
# Voice
# --------------------------------------------------------------------------
VOICE_ENABLED = _bool("VOICE_ENABLED", True)              # Glacier bolke jawab de
TTS_VOICE = _str("TTS_VOICE", "en-IN-PrabhatNeural")       # gentle male. Female: en-IN-NeerjaNeural
TTS_RATE = _str("TTS_RATE", "-4%")                        # e.g. "+10%" faster, "-10%" slower
TTS_PITCH = _str("TTS_PITCH", "-2Hz")
STT_ENGINE = _str("STT_ENGINE", "whisper").lower()        # whisper (offline) | google
WHISPER_MODEL = _str("WHISPER_MODEL", "base")             # tiny | base | small (better, slower)
STT_LANGUAGE = _str("STT_LANGUAGE", "en")                 # "en" works well for Hinglish; "hi" = Devanagari
ALWAYS_LISTEN = _bool("ALWAYS_LISTEN", True)              # hamesha sunta rahe (button dabane ki zaroorat nahi)
FOLLOWUP_SECONDS = _float("FOLLOWUP_SECONDS", 15)          # jawab ke baad itni der "Glacier" bole bina bhi sunega
WAKE_WORDS = _list("WAKE_WORDS", ["glacier", "glasier", "gleshar", "glacia", "glazier", "glassier"])
MIC_DEVICE = _str("MIC_DEVICE")                           # blank = default microphone

# --------------------------------------------------------------------------
# Files & safety
# --------------------------------------------------------------------------
if IS_WINDOWS:
    _default_drives = [d for d in ("C:\\", "D:\\", "E:\\", "F:\\") if os.path.exists(d)]
    _user = os.path.expanduser("~")
    _default_blocked = [
        "C:\\Windows",
        "C:\\Program Files",
        "C:\\Program Files (x86)",
        "C:\\ProgramData",
        "C:\\$Recycle.Bin",
        "C:\\System Volume Information",
        "C:\\Recovery",
        "C:\\Boot",
        os.path.join(_user, "AppData"),
    ]
else:  # developer machine / tests
    _default_drives = [os.path.expanduser("~")]
    _default_blocked = ["/etc", "/usr", "/bin", "/sbin", "/boot", "/proc", "/sys", os.path.join(os.path.expanduser("~"), ".ssh")]

SEARCH_DRIVES = _list("SEARCH_DRIVES", _default_drives, sep="|") or _default_drives
BLOCKED_FOLDERS = _default_blocked + _list("EXTRA_BLOCKED_FOLDERS", [], sep="|")

CONFIRM_TTL_SECONDS = _int("CONFIRM_TTL_SECONDS", 300)
USE_RECYCLE_BIN = _bool("USE_RECYCLE_BIN", True)          # delete -> Recycle Bin (recoverable)
DISABLED_TOOLS = set(_list("DISABLED_TOOLS", []))         # e.g. run_command,run_python
DISABLED_CATEGORIES = set(_list("DISABLED_CATEGORIES", []))  # e.g. control,browser,comms
MAX_TOOL_OUTPUT = _int("MAX_TOOL_OUTPUT", 6000)
SCREEN_AGENT_MAX_STEPS = _int("SCREEN_AGENT_MAX_STEPS", 10)

# --------------------------------------------------------------------------
# Channels
# --------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = _str("TELEGRAM_BOT_TOKEN")
TELEGRAM_ALLOWED_CHAT_ID = _str("TELEGRAM_ALLOWED_CHAT_ID")   # only this chat may command Glacier

API_SERVER_ENABLED = _bool("API_SERVER_ENABLED", False)
API_SERVER_PORT = _int("API_SERVER_PORT", 8765)

EMAIL_ADDRESS = _str("EMAIL_ADDRESS")
EMAIL_APP_PASSWORD = _str("EMAIL_APP_PASSWORD")           # Gmail: App Password (2-step verification on)
IMAP_HOST = _str("IMAP_HOST", "imap.gmail.com")
SMTP_HOST = _str("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = _int("SMTP_PORT", 465)

# --------------------------------------------------------------------------
# Automation / proactive features
# --------------------------------------------------------------------------
HOME_CITY = _str("HOME_CITY")                              # blank = auto-detect from IP
NEWS_FEEDS = _list("NEWS_FEEDS", [
    "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
], sep="|")
DIGEST_ENABLED = _bool("DIGEST_ENABLED", True)
DIGEST_TIME = _str("DIGEST_TIME", "08:00")                 # roz is time (agar PC on ho)
DIGEST_ON_FIRST_START = _bool("DIGEST_ON_FIRST_START", True)  # subah pehli baar start hone par
PROACTIVE_ALERTS = _bool("PROACTIVE_ALERTS", True)         # battery low, disk full, CPU stuck
BATTERY_LOW_PERCENT = _int("BATTERY_LOW_PERCENT", 20)
INDEX_FILES_ON_START = _bool("INDEX_FILES_ON_START", True)  # instant file search

# --------------------------------------------------------------------------
# Browser automation / GUI
# --------------------------------------------------------------------------
BROWSER_CHANNEL = _str("BROWSER_CHANNEL", "chrome")        # chrome | msedge | chromium
BROWSER_HEADLESS = _bool("BROWSER_HEADLESS", False)
START_HIDDEN = _bool("START_HIDDEN", False)                # autostart par window chhupi rahe (tray mein)
TRAY_ENABLED = _bool("TRAY_ENABLED", True)
SINGLE_INSTANCE_PORT = _int("SINGLE_INSTANCE_PORT", 47653)

SECRET_VALUES = [v for v in (GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, EMAIL_APP_PASSWORD, OPENAI_COMPAT_API_KEY) if v and len(v) >= 8 and v != "ollama"]


# --------------------------------------------------------------------------
# Naam / sambodhan ka safety-net (model galti se "Ghanshyam Bhai" bole to bhi theek ho jaye)
# --------------------------------------------------------------------------
import re as _re
_BHAI = _re.compile(r"(?<![\\/\w])(?:Ghanshyam|Ghan\s?shyam|Shyam)\s+(?:bhai(?:ya)?|bhaiya|ji)\b", _re.I)
_FULL = _re.compile(r"(?<![\\/\w.])Ghanshyam(?![\\/\w.])", _re.I)
_BARE_BHAI = _re.compile(r"\b(?:bhai|bhaiya)\b(?=[\s,!.?]|$)", _re.I)


def fix_address(text: str) -> str:
    if not text:
        return text
    t = _BHAI.sub(USER_ADDRESS, text)
    t = _FULL.sub(USER_NAME, t)
    t = _BARE_BHAI.sub("Sir", t)
    return t
