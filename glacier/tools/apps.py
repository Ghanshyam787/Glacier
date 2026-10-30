"""
Glacier Tools: Applications
open / close / list apps, Desktop shortcut.

Fixes vs. old version:
  * launch ka result ASLI hai (os.startfile error deta hai) - "khol diya" jhoothe success nahi
  * installed-apps list cache hoti hai (pehle har baar 2-3 sec ka PowerShell chalta tha)
  * best-match scoring (exact > prefix > word > substring > fuzzy)
  * close_application ab EXACT process match karta hai, pehle polite close; system processes protected
"""

import difflib
import json
import os
import re
import subprocess
import sys
import time

import psutil

import config
import winpaths
from registry import tool
from winutil import run_ps, ps_quote

KNOWN_APPS = {
    "chrome": "chrome.exe", "google chrome": "chrome.exe", "edge": "msedge.exe", "microsoft edge": "msedge.exe",
    "firefox": "firefox.exe", "brave": "brave.exe", "notepad": "notepad.exe", "calculator": "calc.exe",
    "calc": "calc.exe", "vs code": "code", "vscode": "code", "visual studio code": "code",
    "word": "winword.exe", "excel": "excel.exe", "powerpoint": "powerpnt.exe", "outlook": "outlook.exe",
    "spotify": "spotify.exe", "file explorer": "explorer.exe", "explorer": "explorer.exe",
    "cmd": "cmd.exe", "command prompt": "cmd.exe", "powershell": "powershell.exe", "terminal": "wt.exe",
    "paint": "mspaint.exe", "task manager": "taskmgr.exe", "settings": "ms-settings:",
    "control panel": "control.exe", "snipping tool": "snippingtool.exe", "camera": "microsoft.windows.camera:",
    "store": "ms-windows-store:", "microsoft store": "ms-windows-store:", "clock": "ms-clock:",
    "calendar": "outlookcal:", "photos": "ms-photos:", "maps": "bingmaps:", "vlc": "vlc.exe",
    "discord": "discord.exe", "zoom": "zoom.exe", "telegram": "telegram.exe", "steam": "steam.exe",
}

PROTECTED_PROCESSES = {
    "explorer.exe", "csrss.exe", "winlogon.exe", "wininit.exe", "services.exe", "lsass.exe", "svchost.exe",
    "system", "smss.exe", "dwm.exe", "fontdrvhost.exe", "sihost.exe", "ctfmon.exe", "taskhostw.exe",
    "registry", "memory compression", "system idle process", "python.exe", "pythonw.exe", "py.exe",
    "windowsterminal.exe",  # Glacier ko terminal se bhi chalaya ja sakta hai
}

_apps_cache = {"t": 0.0, "apps": []}
_CACHE_TTL = 600


def _start_apps(force: bool = False) -> list:
    """Get-StartApps (normal + Microsoft Store apps), 10 minute cache."""
    now = time.time()
    if not force and _apps_cache["apps"] and now - _apps_cache["t"] < _CACHE_TTL:
        return _apps_cache["apps"]
    try:
        rc, out, _ = run_ps("Get-StartApps | ConvertTo-Json -Compress", timeout=25)
        apps = json.loads(out) if out else []
        if isinstance(apps, dict):
            apps = [apps]
        apps = [a for a in apps if isinstance(a, dict) and a.get("Name") and a.get("AppID")]
    except Exception:
        apps = _apps_cache["apps"]
    _apps_cache.update(t=now, apps=apps)
    return apps


def _score(name: str, kw: str) -> int:
    n = name.lower()
    if n == kw:
        return 100
    if n.startswith(kw):
        return 80
    if re.search(r"\b" + re.escape(kw), n):
        return 60
    if kw in n:
        return 45
    ratio = difflib.SequenceMatcher(None, kw, n).ratio()
    return int(ratio * 50) if ratio >= 0.72 else 0


def _find_installed_app(keyword: str):
    """(name, appid) ya None."""
    kw = keyword.lower().strip()
    best, best_score = None, 0
    for app in _start_apps():
        s = _score(app["Name"], kw)
        if s > best_score:
            best, best_score = app, s
    if best and best_score >= 38:
        return best["Name"], best["AppID"]
    return None


def _startfile(target: str):
    os.startfile(target)  # type: ignore[attr-defined]  # Windows only; FileNotFoundError agar na mile


@tool(category="apps", label="Open app")
def open_application(app_name: str) -> str:
    """
    Open any installed Windows application by name - desktop programs AND Microsoft Store apps
    (WhatsApp, ChatGPT, Spotify ...). Use this FIRST for any 'open X' request. Only use open_website
    if this says the app was not found or the user explicitly wants the website.
    """
    if not config.IS_WINDOWS:
        return "App kholna sirf Windows par supported hai."
    key = app_name.strip().lower()
    if not key:
        return "Kaunsa app kholna hai?"

    # 1) known quick commands
    cmd = KNOWN_APPS.get(key)
    if cmd:
        try:
            _startfile(cmd)
            return f"{app_name} khol diya."
        except (FileNotFoundError, OSError):
            pass

    # 2) everything installed (incl. Store apps)
    found = _find_installed_app(key)
    if found:
        name, app_id = found
        try:
            if os.path.exists(app_id):
                _startfile(app_id)
            else:
                subprocess.Popen(["explorer.exe", f"shell:appsFolder\\{app_id}"], creationflags=0x08000000)
            return f"{name} khol diya."
        except Exception as e:
            return f"{name} mil gaya par khol nahi paya: {e}"

    # 3) bare .exe registered in App Paths
    if re.fullmatch(r"[\w .\-]+", key):
        try:
            _startfile(key.replace(" ", "") + ".exe")
            return f"{app_name} khol diya."
        except (FileNotFoundError, OSError):
            pass

    return (f"'{app_name}' naam ka koi installed app is PC pe nahi mila. "
            f"Agar ye website hai to open_website use karo.")


@tool(category="apps", label="Desktop shortcut")
def create_desktop_shortcut(app_name: str) -> str:
    """
    Create a Desktop shortcut for an installed application (works for Store apps like WhatsApp too,
    with the correct icon). Use when the user says 'shortcut banao' / 'Desktop pe daal do'.
    """
    found = _find_installed_app(app_name.strip().lower())
    if not found:
        return f"'{app_name}' naam ka koi installed app nahi mila, shortcut nahi bana saka."
    name, app_id = found
    desktop = winpaths.get_desktop()
    safe_name = re.sub(r'[\\/:*?"<>|]', "", name.strip()) or "App"

    if os.path.exists(app_id):
        lnk = os.path.join(desktop, f"{safe_name}.lnk")
        script = (f"$s = New-Object -ComObject WScript.Shell; $sc = $s.CreateShortcut({ps_quote(lnk)}); "
                  f"$sc.TargetPath = {ps_quote(app_id)}; $sc.Save()")
    else:
        # Store app: Start menu se drag jaisa tareeka (sahi icon ke saath)
        script = ("$shell = New-Object -ComObject Shell.Application; "
                  f"$item = $shell.NameSpace('shell:AppsFolder').ParseName({ps_quote(app_id)}); "
                  f"$shell.NameSpace({ps_quote(desktop)}).CopyHere($item)")
    try:
        before = set(os.listdir(desktop)) if os.path.isdir(desktop) else set()
        run_ps(script, timeout=25)
        time.sleep(0.8)
        after = set(os.listdir(desktop)) if os.path.isdir(desktop) else set()
    except Exception as e:
        return f"Shortcut banane mein error: {e}"
    if any(f.lower().endswith(".lnk") for f in after - before) or \
            any(safe_name.lower() in f.lower() and f.lower().endswith(".lnk") for f in after):
        return f"{name} ka shortcut Desktop pe bana diya."
    return f"{name} mil gaya par shortcut Desktop pe dikh nahi raha - manually check karo."


def _target_names(key: str) -> set:
    names = set()
    mapped = KNOWN_APPS.get(key)
    if mapped and mapped.endswith(".exe"):
        names.add(mapped.lower())
    names.add(key if key.endswith(".exe") else key + ".exe")
    names.add(key.replace(" ", "") + ".exe")
    return names


def _matching_processes(key: str) -> list:
    exact = _target_names(key)
    procs = []
    me = os.getpid()
    for p in psutil.process_iter(["name", "pid"]):
        try:
            pname = (p.info["name"] or "").lower()
            if p.info["pid"] == me or pname in PROTECTED_PROCESSES:
                continue
            stem = pname[:-4] if pname.endswith(".exe") else pname
            k = key.replace(" ", "")
            if pname in exact or stem == key or stem == k or (
                    len(k) >= 4 and re.match(rf"^{re.escape(k)}[._\-]", stem)):
                procs.append(p)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return procs


@tool(category="apps", label="Close app")
def close_application(app_name: str, force: bool = False) -> str:
    """
    Close a running application by name. First asks it to close politely (so unsaved-work prompts appear).
    If it does not close, tell the user and only then call again with force=True.
    """
    key = app_name.strip().lower()
    if len(key) < 2:
        return "App ka naam batao."
    if key in {n[:-4] for n in PROTECTED_PROCESSES if n.endswith(".exe")} | {"explorer", "windows", "system"}:
        return f"'{app_name}' system ka zaroori hissa hai, isse band nahi karunga."
    procs = _matching_processes(key)
    if not procs:
        return f"{app_name} chalu nahi mila."
    names = sorted({(p.info["name"] or "") for p in procs})
    if not force:
        for n in names:
            try:
                subprocess.run(["taskkill", "/IM", n], capture_output=True, timeout=10, creationflags=0x08000000)
            except Exception:
                pass
        time.sleep(2.0)
        alive = [p for p in procs if p.is_running()]
        if not alive:
            return f"{app_name} band kar diya."
        return (f"{app_name} ko band hone ko bola par abhi chal raha hai (shayad save karne ka sawal pooch raha hai). "
                f"User se pooch ke force=True se band kar sakte ho.")
    killed = 0
    for p in procs:
        try:
            p.terminate()
            killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return f"{app_name} force band kiya ({killed} processes)."


@tool(category="apps", label="Running apps")
def list_running_apps() -> str:
    """List the apps that currently have a visible window (what the user sees on screen)."""
    if config.IS_WINDOWS:
        try:
            rc, out, _ = run_ps(
                "Get-Process | Where-Object {$_.MainWindowTitle} | "
                "Select-Object Name,MainWindowTitle | ConvertTo-Json -Compress", timeout=20)
            items = json.loads(out) if out else []
            if isinstance(items, dict):
                items = [items]
            lines = [f"- {i['Name']}: {i['MainWindowTitle'][:70]}" for i in items]
            return "Abhi ye apps khule hain:\n" + "\n".join(lines) if lines else "Koi visible app nahi mila."
        except Exception:
            pass
    names = sorted({(p.info["name"] or "") for p in psutil.process_iter(["name"]) if p.info["name"]})
    return "Chalte processes: " + ", ".join(names[:80])
