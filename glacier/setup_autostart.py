"""
Glacier - Auto-start (Startup folder).
  .venv\\Scripts\\python setup_autostart.py            -> laptop on hote hi Glacier chalu (tray mein)
  .venv\\Scripts\\python setup_autostart.py --remove   -> autostart hata do
"""

import os
import subprocess
import sys

STARTUP_FOLDER = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Microsoft", "Windows",
                              "Start Menu", "Programs", "Startup")
GLACIER_DIR = os.path.dirname(os.path.abspath(__file__))
LAUNCHER_PATH = os.path.join(STARTUP_FOLDER, "start_glacier.bat")
TASK_NAME = "GlacierAssistant"


def pythonw() -> str:
    venv = os.path.join(GLACIER_DIR, ".venv", "Scripts", "pythonw.exe")
    if os.path.exists(venv):
        return venv
    exe = sys.executable
    return exe[:-10] + "pythonw.exe" if exe.lower().endswith("python.exe") else exe


def remove_old_task():
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        f'Unregister-ScheduledTask -TaskName "{TASK_NAME}" -Confirm:$false -ErrorAction SilentlyContinue'],
                       capture_output=True, timeout=15)
    except Exception:
        pass


def main():
    if os.name != "nt":
        print("Ye sirf Windows ke liye hai.")
        return
    if "--remove" in sys.argv:
        if os.path.exists(LAUNCHER_PATH):
            os.remove(LAUNCHER_PATH)
            print("Autostart hata diya.")
        else:
            print("Autostart set hi nahi tha.")
        return
    if not os.path.isdir(STARTUP_FOLDER):
        print(f"Startup folder nahi mila: {STARTUP_FOLDER}")
        return
    remove_old_task()
    with open(LAUNCHER_PATH, "w", encoding="utf-8") as f:
        f.write(f'@echo off\r\ncd /d "{GLACIER_DIR}"\r\nstart "" "{pythonw()}" "{GLACIER_DIR}\\main_gui.py" --background\r\n')
    print("Autostart set ho gaya. Agli baar PC on hote hi Glacier tray mein chalu hoga.")
    print("Hatane ke liye:  python setup_autostart.py --remove")


if __name__ == "__main__":
    main()
