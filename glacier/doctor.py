"""
Glacier Doctor - sab kuchh check karta hai aur batata hai kya theek karna hai.
Chalao:  python doctor.py        (ya: python doctor.py --selftest  = AI call bhi test karega)
"""

import importlib
import os
import socket
import sys

OK, BAD, WARN = "[ OK ]", "[FAIL]", "[WARN]"
problems = 0


def line(tag, msg):
    global problems
    if tag == BAD:
        problems += 1
    print(f"{tag} {msg}")


def check_import(mod, pip=None, required=True):
    try:
        importlib.import_module(mod)
        line(OK, f"{mod}")
    except Exception as e:
        line(BAD if required else WARN,
             f"{mod} nahi mila ({'zaroori' if required else 'optional'}) -> pip install {pip or mod}   [{type(e).__name__}]")


def main() -> int:
    print("=== Glacier Doctor ===\n")
    v = sys.version_info
    line(OK if (3, 10) <= v[:2] < (3, 14) else WARN, f"Python {v.major}.{v.minor}.{v.micro}" +
         ("" if (3, 10) <= v[:2] < (3, 14) else "  (Python 3.12 recommended)"))
    line(OK if os.name == "nt" else WARN, "Windows" if os.name == "nt" else "Windows nahi hai - kuchh tools (apps, volume...) kaam nahi karenge")

    print("\n-- Zaroori libraries")
    for m, p in [("google.genai", "google-genai"), ("psutil", None), ("requests", None), ("bs4", "beautifulsoup4"),
                 ("webview", "pywebview"), ("edge_tts", "edge-tts"), ("PIL", "pillow"), ("send2trash", "Send2Trash")]:
        check_import(m, p)
    print("\n-- Optional libraries")
    for m, p in [("sounddevice", None), ("numpy", None), ("faster_whisper", "faster-whisper"), ("speech_recognition", "SpeechRecognition"),
                 ("pycaw", None), ("pyautogui", None), ("pystray", None), ("ddgs", None), ("playwright", None),
                 ("pypdf", None), ("docx", "python-docx"), ("openpyxl", None), ("mcp", None)]:
        check_import(m, p, required=False)

    print("\n-- Glacier")
    try:
        import config
        import db  # noqa: F401
        import registry  # noqa: F401
        import tools
        import skillsys
        line(OK, f"{len(registry.TOOLS)} tools load hue")
        for k, e in {**tools.LOAD_ERRORS, **skillsys.LOAD_ERRORS}.items():
            line(WARN, f"module '{k}' load nahi hua: {e}")
    except Exception as e:
        line(BAD, f"Glacier load nahi hua: {type(e).__name__}: {e}")
        return 1

    if config.has_api_key():
        line(OK, "GEMINI_API_KEY mili (.env)")
        import engines
        try:
            models = engines.discover_models()
            line(OK, f"Gemini se connection theek. Models: {', '.join(models[:4]) or '-'}")
            line(OK, f"Abhi ka model: {engines.pick_model()}")
        except Exception as e:
            line(BAD, f"Gemini se connect nahi hua: {str(e)[:160]}")
    else:
        line(BAD, "GEMINI_API_KEY nahi hai. .env kholo aur key daalo (free: https://aistudio.google.com/apikey)")

    try:
        import engines
        c = engines.compat_config()
        line(OK if c else WARN, f"Backup engine (Ollama): {c[1]}" if c else "Ollama nahi mila (optional - offline backup ke liye)")
    except Exception:
        pass

    print("\n-- Voice")
    try:
        import voice
        mics = voice.list_microphones()
        line(OK if mics else WARN, f"Mic: {mics[0]}" if mics else "Koi microphone nahi mila")
    except Exception as e:
        line(WARN, f"Voice check nahi hua: {type(e).__name__}")

    print("\n-- Extras")
    line(OK if config.TELEGRAM_BOT_TOKEN else WARN, "Telegram bot " + ("set hai" if config.TELEGRAM_BOT_TOKEN else "set nahi (optional)"))
    line(OK if config.EMAIL_ADDRESS and config.EMAIL_APP_PASSWORD else WARN, "Email " + ("set hai" if config.EMAIL_ADDRESS else "set nahi (optional)"))
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        line(OK, "Playwright installed (browser control). Pehli baar: python -m playwright install chromium")
    except Exception:
        line(WARN, "Playwright nahi hai (optional, browser control ke liye)")
    try:
        socket.create_connection(("generativelanguage.googleapis.com", 443), timeout=5).close()
        line(OK, "Internet / Gemini server reachable")
    except OSError:
        line(BAD, "Internet ya Gemini server tak nahi pahunch pa raha")

    if "--selftest" in sys.argv and config.has_api_key():
        print("\n-- Selftest (1 AI request use hoga)")
        import brain
        r = brain.ask_glacier("Bas ek shabd mein jawab do: 2+2 kitna hota hai? (calculate tool use karo)", session="doctor", ephemeral=True)
        line(OK if r and "Kuchh galat" not in r else BAD, f"Glacier ka jawab: {r[:120]}")

    print(f"\n{'Sab theek hai!' if not problems else f'{problems} cheez(en) theek karni hain (upar [FAIL] dekho).'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
