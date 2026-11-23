"""
Glacier - GUI bridge: is class ke PUBLIC methods dashboard JS se window.pywebview.api.<name>() se bulaye jaate hain.
ZAROORI: pywebview public attributes ko recursively scan karta hai - isliye window ya koi bhi bada object
yahan public attribute mat banao (sirf _underscore wale). Isi se pehle "maximum recursion depth" error aaya tha.
"""

import json
import os
import re
import threading

import brain
import config
import events
import registry
import memory
import registry as _registry
import safety
import services
import voice
import winpaths
from activity import get_activity as _get_activity
from activity import get_activity_full as _get_activity_full
from tools import reminders as _rem
from tools.reminders import get_reminders_list
from tools.system import get_vitals as _get_vitals


class Api:
    def __init__(self):
        self._window = None
        self._mic_state = "muted"
        events.subscribe(self._on_event)

    # ---------------- Python -> JS (sab private)
    def _js(self, code: str):
        if self._window is None:
            return
        try:
            self._window.evaluate_js(code)
        except Exception:
            pass

    def _on_event(self, kind, payload):
        if kind == "notify":
            self._js(f"window.glacierPush && window.glacierPush({json.dumps(payload, ensure_ascii=False)})")

    def _wake_state(self, state: str):
        self._mic_state = state
        self._js(f"window.glacierMic && window.glacierMic({json.dumps(state)})")

    def _wake_command(self, text: str):
        """Voice se aayi command: jawab do + bolo + dashboard par dikhao."""
        self._js(f"window.glacierHeard && window.glacierHeard({json.dumps(text, ensure_ascii=False)})")
        reply = brain.ask_glacier(text)
        voice.speak_if_enabled(reply)
        self._js(f"window.glacierReply && window.glacierReply({json.dumps(text, ensure_ascii=False)}, {json.dumps(reply, ensure_ascii=False)})")

    # ---------------- JS -> Python (public)
    def send_command(self, text: str) -> str:
        if not text or not text.strip():
            return ""
        reply = brain.ask_glacier(text.strip())
        threading.Thread(target=voice.speak_if_enabled, args=(reply,), daemon=True).start()
        return reply

    def mic_status(self) -> dict:
        """{'available': bool, 'state': listening|hearing|thinking|speaking|muted}"""
        w = services.wake
        return {"available": w is not None and w.is_alive(), "state": w.state if w else "off"}

    def toggle_mic(self) -> dict:
        """Mic ko mute/unmute (default: hamesha ON)."""
        w = services.wake
        if w is None or not w.is_alive():
            return {"available": False, "state": "off"}
        w.set_muted(not w.paused.is_set())
        return self.mic_status()

    def stop_speaking(self) -> bool:
        voice.stop_speaking()
        return True

    def reset_chat(self) -> str:
        brain.reset_session("local")
        return "Nayi baat-cheet shuru."

    def feedback(self, rating: int) -> str:
        return brain.give_feedback(int(rating))

    def get_vitals(self) -> dict:
        return _get_vitals()

    def get_reminders(self) -> list:
        return get_reminders_list()

    def get_activity(self) -> list:
        return _get_activity()

    def activity_all(self, limit: int = 300) -> list:
        return _get_activity_full(limit)

    # ---------------- Reminders manager (View all)
    def reminders_all(self, view: str = "all") -> list:
        try:
            return _rem.reminders_all(str(view or "all"))
        except Exception as e:
            registry.log_error("api.reminders_all", e)
            return []

    def reminder_add(self, text: str, when: str, repeat: str = "") -> dict:
        try:
            return _rem.reminder_add(str(text or ""), str(when or ""), str(repeat or ""))
        except Exception as e:
            registry.log_error("api.reminder_add", e)
            return {"ok": False, "msg": "Kuchh gadbad hui: " + str(e)[:80]}

    def reminder_update(self, rid: int, text: str, when: str, repeat: str = "") -> dict:
        try:
            return _rem.reminder_update(int(rid), str(text or ""), str(when or ""), str(repeat or ""))
        except Exception as e:
            registry.log_error("api.reminder_update", e)
            return {"ok": False, "msg": "Kuchh gadbad hui: " + str(e)[:80]}

    def reminder_delete(self, rid: int) -> dict:
        try:
            return _rem.reminder_delete(int(rid))
        except Exception as e:
            registry.log_error("api.reminder_delete", e)
            return {"ok": False, "msg": "Kuchh gadbad hui: " + str(e)[:80]}

    def get_status(self) -> dict:
        try:
            return brain.status()
        except Exception as e:
            return {"error": str(e)[:100]}

    # ---------------- Chat panel
    def get_history(self, limit: int = 30) -> list:
        try:
            return [{"role": r, "text": t} for r, t in memory.recent_messages("local", int(limit))]
        except Exception:
            return []

    # ---------------- Files panel
    def known_folders(self) -> list:
        f = winpaths.known_folders()
        return [{"name": k.title(), "path": v} for k, v in f.items() if v]

    def list_dir(self, path: str) -> dict:
        p = os.path.abspath(os.path.expanduser(str(path or "")))
        if not (safety.is_allowed_path(p) and os.path.isdir(p)):
            return {"error": "Ye folder khul nahi sakta (protected ya nahi mila).", "path": p, "entries": []}
        out = []
        try:
            for e in os.scandir(p):
                try:
                    out.append({"name": e.name, "path": e.path, "dir": e.is_dir(),
                                "size": 0 if e.is_dir() else e.stat().st_size})
                except OSError:
                    continue
        except OSError as ex:
            return {"error": str(ex)[:100], "path": p, "entries": []}
        out.sort(key=lambda x: (not x["dir"], x["name"].lower()))
        parent = os.path.dirname(p)
        return {"path": p, "parent": parent if parent != p and safety.is_allowed_path(parent) else "",
                "entries": out[:250], "error": ""}

    def search_files(self, query: str) -> dict:
        tokens = [t for t in re.split(r"\s+", str(query or "").strip()) if t]
        if not tokens:
            return {"rows": [], "note": "Kuchh likho jo dhundna hai."}
        import fileindex
        rows = []
        note = ""
        if fileindex.is_ready():
            rows = [{"name": os.path.basename(r["path"]), "path": r["path"], "dir": bool(r["is_dir"]), "size": r["size"]}
                    for r in fileindex.search(tokens, limit=60)]
        else:
            note = "Index abhi ban raha hai, isliye sirf Desktop/Downloads/Documents/Pictures mein dhundha."
            low = [t.lower() for t in tokens]
            for base in winpaths.known_folders().values():
                for root, dirs, files in os.walk(base):
                    if root[len(base):].count(os.sep) >= 3:
                        dirs[:] = []
                    for n in dirs + files:
                        if all(t in n.lower() for t in low):
                            fp = os.path.join(root, n)
                            rows.append({"name": n, "path": fp, "dir": os.path.isdir(fp), "size": 0})
                    if len(rows) >= 60:
                        break
        rows = [r for r in rows if safety.is_allowed_path(r["path"])]
        return {"rows": rows[:60], "note": note if rows or note else "Kuchh nahi mila."}

    def open_item(self, path: str) -> str:
        from tools import files
        return files.open_path(str(path))

    # ---------------- Tools panel
    def get_capabilities(self) -> list:
        out = []
        for cat, names in sorted(_registry.tools_by_category().items()):
            items = []
            for n in sorted(names):
                fn = _registry.TOOLS.get(n)
                doc = ""
                try:
                    doc = ((getattr(fn, "__doc__", "") or "").strip().splitlines() or [""])[0][:110]
                except Exception:
                    pass
                items.append({"name": n, "doc": doc})
            out.append({"category": cat, "tools": items})
        return out

    # ---------------- Settings panel
    _EDITABLE = {"VOICE_ENABLED": "bool", "REQUIRE_WAKE_WORD": "bool", "TTS_VOICE": "voice", "TTS_RATE": "rate", "STT_LANGUAGE": "lang"}

    def get_settings(self) -> dict:
        st = self.get_status()
        return {"VOICE_ENABLED": bool(config.VOICE_ENABLED), "REQUIRE_WAKE_WORD": bool(config.REQUIRE_WAKE_WORD),
                "TTS_VOICE": config.TTS_VOICE, "TTS_RATE": config.TTS_RATE, "STT_LANGUAGE": config.STT_LANGUAGE,
                "name": config.USER_ADDRESS, "model": st.get("model", "-"),
                "quota_used": st.get("quota_used"), "quota_limit": st.get("quota_limit"),
                "resets_at": st.get("resets_at"), "tools": st.get("tools"), "mic": self.mic_status()}

    def set_setting(self, key: str, value) -> dict:
        kind = self._EDITABLE.get(key)
        if not kind:
            return {"ok": False, "error": "ye setting yahan se badal nahi sakti"}
        if kind == "bool":
            value = bool(value)
        elif kind == "voice":
            value = str(value)
            if not re.fullmatch(r"[a-z]{2}-[A-Z]{2}-[A-Za-z]+Neural", value):
                return {"ok": False, "error": "galat voice naam"}
        elif kind == "rate":
            value = str(value)
            if not re.fullmatch(r"[+-]\d{1,2}%", value):
                return {"ok": False, "error": "galat speed"}
        elif kind == "lang":
            value = str(value).lower()
            if not re.fullmatch(r"auto|[a-z]{2,3}", value):
                return {"ok": False, "error": "galat bhasha code"}
        setattr(config, key, value)
        try:
            self._persist_env(key, "true" if value is True else "false" if value is False else value)
        except Exception as e:
            _registry.log_error("persist setting", e)
        return {"ok": True, "settings": self.get_settings()}

    def test_voice(self) -> bool:
        voice.speak(f"Namaste {config.USER_ADDRESS}, main Glacier hoon. Ye meri awaaz hai.")
        return True

    def test_language(self, code: str) -> bool:
        """Settings se: chuni hui bhasha mein ek chhota vaakya bolke awaaz check karo."""
        import langs
        txt = langs.SAMPLES.get(str(code))
        if not txt:
            return False
        voice.remember_lang(txt, str(code))
        voice.speak(txt)
        return True

    def language_codes(self) -> list:
        import langs
        return sorted(langs.SAMPLES)

    @staticmethod
    def _persist_env(key: str, value: str):
        path = os.path.join(config.BASE_DIR, ".env")
        lines = []
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                lines = f.read().splitlines()
        done = False
        for i, ln in enumerate(lines):
            if re.match(rf"\s*{re.escape(key)}\s*=", ln):
                lines[i] = f"{key}={value}"
                done = True
        if not done:
            lines.append(f"{key}={value}")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
