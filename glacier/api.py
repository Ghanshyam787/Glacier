"""
Glacier - GUI bridge: is class ke PUBLIC methods dashboard JS se window.pywebview.api.<name>() se bulaye jaate hain.
ZAROORI: pywebview public attributes ko recursively scan karta hai - isliye window ya koi bhi bada object
yahan public attribute mat banao (sirf _underscore wale). Isi se pehle "maximum recursion depth" error aaya tha.
"""

import json
import threading

import brain
import config
import events
import registry
import services
import voice
from activity import get_activity as _get_activity
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

    def get_status(self) -> dict:
        try:
            return brain.status()
        except Exception as e:
            return {"error": str(e)[:100]}
