"""
Glacier - Shared startup (main.py aur main_gui.py dono yahin se sab chalu karte hain)
"""

import socket
import threading

import config
import notify
import registry

_started = False
_lock_sock = None
wake = None


def acquire_single_instance() -> bool:
    """Ek hi Glacier chale (autostart + manual double-launch se bachav)."""
    global _lock_sock
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1) if hasattr(socket, "SO_EXCLUSIVEADDRUSE") else None
        s.bind(("127.0.0.1", config.SINGLE_INSTANCE_PORT))
        s.listen(1)
    except OSError:
        return False
    _lock_sock = s
    return True


def start_all(on_wake_command=None, wake_state_cb=None):
    """Background services. Safe to call twice."""
    global _started, wake
    if _started:
        return
    _started = True
    import tools  # noqa: F401  (registers all tools)

    try:
        import voice
        notify.register_sink("voice", "speak", voice.speak_if_enabled)
    except Exception as e:
        registry.log_error("voice sink", e)

    try:
        from channels import telegram_bot
        if telegram_bot.start():
            notify.register_sink("telegram", "remote", lambda t: telegram_bot.send_text(t) if config.TELEGRAM_ALLOWED_CHAT_ID else None)
    except Exception as e:
        registry.log_error("telegram start", e)

    try:
        from channels import api_server
        api_server.start()
    except Exception as e:
        registry.log_error("api start", e)

    try:
        import scheduler
        scheduler.start()
    except Exception as e:
        registry.log_error("scheduler start", e)

    if config.INDEX_FILES_ON_START:
        try:
            import fileindex
            fileindex.start_background()
        except Exception as e:
            registry.log_error("fileindex start", e)

    if config.STT_ENGINE == "whisper":
        def _prewarm():  # Whisper model pehle se download/load, taaki pehla mic click na atke
            try:
                import voice
                if voice.mic_available():
                    voice._get_whisper()
                    print("[Voice] Whisper taiyar hai.")
            except Exception as e:
                registry.log_error("whisper prewarm", e)
        threading.Thread(target=_prewarm, daemon=True, name="glacier-whisper-warm").start()

    if config.ALWAYS_LISTEN and on_wake_command:
        try:
            import voice
            if voice.mic_available():
                wake = voice.WakeListener(on_wake_command, wake_state_cb)
                wake.start()
            else:
                print("[Voice] Microphone nahi mila - hamesha sunna chalu nahi hua.")
        except Exception as e:
            registry.log_error("wake start", e)
