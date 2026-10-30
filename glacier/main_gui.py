"""
Glacier - Desktop dashboard (pywebview).
  python main_gui.py               -> window ke saath
  python main_gui.py --background  -> chhupa hua (tray icon se kholo)  [autostart yahi use karta hai]
"""

import os
import sys
import threading

import config
import registry

DASHBOARD_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "glacier_dashboard.html")


def _make_tray(window, quit_cb):
    try:
        import pystray
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    img = Image.new("RGB", (64, 64), (5, 8, 15))
    d = ImageDraw.Draw(img)
    d.polygon([(32, 6), (56, 32), (32, 58), (8, 32)], outline=(120, 220, 255), width=4)
    d.polygon([(32, 20), (44, 32), (32, 44), (20, 32)], fill=(120, 220, 255))
    menu = pystray.Menu(
        pystray.MenuItem("Glacier kholo", lambda: window.show(), default=True),
        pystray.MenuItem("Chhupao", lambda: window.hide()),
        pystray.MenuItem("Band karo", lambda: quit_cb()),
    )
    return pystray.Icon("glacier", img, config.ASSISTANT_NAME, menu)


def main():
    background = "--background" in sys.argv or config.START_HIDDEN
    import services
    if not services.acquire_single_instance():
        print("Glacier pehle se chal raha hai.")
        return
    if not os.path.exists(DASHBOARD_PATH):
        print(f"ERROR: dashboard file nahi mili: {DASHBOARD_PATH}")
        return
    import webview
    from api import Api

    api = Api()
    window = webview.create_window(
        config.ASSISTANT_NAME, DASHBOARD_PATH, js_api=api, width=1280, height=800,
        min_size=(900, 600), background_color="#05080F", hidden=background)
    api._window = window
    state = {"quitting": False, "tray": None}

    def quit_app():
        state["quitting"] = True
        try:
            if state["tray"]:
                state["tray"].stop()
        except Exception:
            pass
        try:
            window.destroy()
        except Exception:
            pass
        os._exit(0)

    tray = _make_tray(window, quit_app) if config.TRAY_ENABLED else None
    state["tray"] = tray
    if tray:
        def on_closing():
            if state["quitting"]:
                return True
            window.hide()      # X dabane par tray mein chala jaye, band na ho
            return False
        window.events.closing += on_closing
        threading.Thread(target=tray.run, daemon=True, name="glacier-tray").start()

    def boot():
        services.start_all(on_wake_command=api._wake_command, wake_state_cb=api._wake_state)
    threading.Thread(target=boot, daemon=True).start()
    webview.start()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        registry.log_error("main_gui", e)
        raise
