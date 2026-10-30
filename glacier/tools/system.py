"""
Glacier Tools: System control & monitoring
status, volume, brightness, media keys, lock/sleep/shutdown, clipboard, dark mode, network, processes.
"""

import ctypes
import os
import subprocess
import time
from datetime import timedelta

import psutil

import config
import safety
from registry import tool
from winutil import CREATE_NO_WINDOW, ps_quote, run_ps

# ---------------------------------------------------------------------------
# Monitoring
# ---------------------------------------------------------------------------


def get_vitals() -> dict:
    """GUI gauges ke liye plain numbers (tool nahi)."""
    cpu = psutil.cpu_percent(interval=0.3)
    ram = psutil.virtual_memory().percent
    try:
        b = psutil.sensors_battery()
    except Exception:
        b = None
    return {"cpu": round(cpu), "ram": round(ram), "battery": round(b.percent) if b else None,
            "plugged": bool(b.power_plugged) if b else None}


@tool(category="system", label="System status")
def get_system_status() -> str:
    """CPU, RAM, every disk, battery, uptime and network speed - a quick health report of this PC."""
    cpu = psutil.cpu_percent(interval=0.8)
    ram = psutil.virtual_memory()
    lines = [f"CPU: {cpu}% ({psutil.cpu_count()} threads)",
             f"RAM: {ram.percent}% ({ram.used / 1024**3:.1f} / {ram.total / 1024**3:.1f} GB)"]
    for part in psutil.disk_partitions(all=False):
        if "cdrom" in part.opts or not part.fstype:
            continue
        try:
            u = psutil.disk_usage(part.mountpoint)
            lines.append(f"Disk {part.mountpoint}: {u.percent}% used ({u.free / 1024**3:.0f} GB free of {u.total / 1024**3:.0f} GB)")
        except OSError:
            continue
    try:
        b = psutil.sensors_battery()
        if b:
            left = ""
            if not b.power_plugged and b.secsleft and b.secsleft > 0:
                left = f", ~{str(timedelta(seconds=int(b.secsleft)))[:-3]} baaki"
            lines.append(f"Battery: {b.percent:.0f}% ({'charging' if b.power_plugged else 'on battery'}{left})")
    except Exception:
        pass
    up = time.time() - psutil.boot_time()
    lines.append(f"Uptime: {str(timedelta(seconds=int(up)))}")
    return "\n".join(lines)


@tool(category="system", label="Top processes")
def get_disk_hogs(top_n: int = 6) -> str:
    """Which running programs use the most RAM and CPU right now (helps when the PC feels slow)."""
    procs = []
    for p in psutil.process_iter(["name", "memory_percent"]):
        try:
            p.cpu_percent(None)
            procs.append(p)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    time.sleep(0.6)
    rows = []
    for p in procs:
        try:
            rows.append((p.info["name"], p.info["memory_percent"] or 0, p.cpu_percent(None)))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    top_mem = sorted(rows, key=lambda r: -r[1])[:top_n]
    top_cpu = sorted(rows, key=lambda r: -r[2])[:3]
    return ("Sabse zyada RAM:\n" + "\n".join(f"- {n}: {m:.1f}%" for n, m, _ in top_mem) +
            "\nSabse zyada CPU:\n" + "\n".join(f"- {n}: {c:.0f}%" for n, _, c in top_cpu))


@tool(category="system", label="Network info")
def get_network_info() -> str:
    """Current network: Wi-Fi name, IP addresses, and whether the internet works."""
    lines = []
    if config.IS_WINDOWS:
        try:
            p = subprocess.run(["netsh", "wlan", "show", "interfaces"], capture_output=True, timeout=8,
                               creationflags=CREATE_NO_WINDOW)
            txt = p.stdout.decode("utf-8", "replace")
            for ln in txt.splitlines():
                s = ln.strip()
                if s.startswith(("SSID", "Signal")) and "BSSID" not in s:
                    lines.append(s)
        except Exception:
            pass
    for name, addrs in psutil.net_if_addrs().items():
        for a in addrs:
            if a.family.name == "AF_INET" and not a.address.startswith(("127.", "169.254.")):
                lines.append(f"{name}: {a.address}")
    try:
        import socket
        socket.create_connection(("1.1.1.1", 443), timeout=3).close()
        lines.append("Internet: chal raha hai")
    except OSError:
        lines.append("Internet: NAHI chal raha")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Keys / volume / brightness
# ---------------------------------------------------------------------------
_VK = {"vol_up": 0xAF, "vol_down": 0xAE, "mute": 0xAD, "next": 0xB0, "prev": 0xB1, "stop": 0xB2, "play_pause": 0xB3}


def _press_vk(vk: int, times: int = 1):
    user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    for _ in range(times):
        user32.keybd_event(vk, 0, 0, 0)
        user32.keybd_event(vk, 0, 2, 0)
        time.sleep(0.01)


def _endpoint_volume():
    from comtypes import CLSCTX_ALL  # noqa
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    dev = AudioUtilities.GetSpeakers()
    ev = getattr(dev, "EndpointVolume", None)
    if ev is not None:
        return ev
    from ctypes import POINTER, cast
    iface = dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(iface, POINTER(IAudioEndpointVolume))


@tool(category="system", label="Volume")
def set_volume(level: int = -1, change: int = 0, mute: str = "") -> str:
    """
    Control speaker volume. level=0-100 sets an exact volume; change=+10/-10 adjusts relatively;
    mute='on'|'off'|'toggle' mutes/unmutes.
    """
    if not config.IS_WINDOWS:
        return "Volume control sirf Windows par."
    try:
        ev = _endpoint_volume()
        if mute:
            cur = bool(ev.GetMute())
            ev.SetMute({"on": 1, "off": 0}.get(mute.lower(), 0 if cur else 1), None)
            return "Mute kar diya." if ev.GetMute() else "Unmute kar diya."
        cur_level = round(ev.GetMasterVolumeLevelScalar() * 100)
        target = level if level >= 0 else cur_level + change
        target = max(0, min(100, int(target)))
        ev.SetMasterVolumeLevelScalar(target / 100.0, None)
        return f"Volume {target}% kar diya."
    except Exception:
        pass  # pycaw nahi hai - media keys se (har press ~2%)
    try:
        if mute:
            _press_vk(_VK["mute"])
            return "Mute toggle kar diya."
        if level >= 0:
            _press_vk(_VK["vol_down"], 50)
            _press_vk(_VK["vol_up"], round(max(0, min(100, level)) / 2))
            return f"Volume lagbhag {level}% kar diya."
        n = max(1, abs(change) // 2)
        _press_vk(_VK["vol_up"] if change > 0 else _VK["vol_down"], n)
        return f"Volume {'badha' if change > 0 else 'ghata'} diya."
    except Exception as e:
        return f"Volume change nahi ho paya: {e}"


@tool(category="system", label="Media key")
def media_control(action: str) -> str:
    """Press a media key: play_pause | next | prev | stop. Works for Spotify, YouTube, VLC etc."""
    a = (action or "").lower().replace(" ", "_").replace("-", "_")
    a = {"play": "play_pause", "pause": "play_pause", "previous": "prev", "skip": "next"}.get(a, a)
    if a not in ("play_pause", "next", "prev", "stop"):
        return "action: play_pause | next | prev | stop"
    if not config.IS_WINDOWS:
        return "Sirf Windows par."
    _press_vk(_VK[a])
    return f"Media: {a} bhej diya."


@tool(category="system", label="Brightness")
def set_brightness(level: int) -> str:
    """Set laptop screen brightness (0-100). Works on built-in laptop displays."""
    level = max(0, min(100, int(level)))
    try:
        rc, out, err = run_ps(
            "Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods | "
            f"Invoke-CimMethod -MethodName WmiSetBrightness -Arguments @{{Timeout=1; Brightness={level}}} | Out-Null",
            timeout=15)
        if rc != 0 or err:
            return f"Brightness change nahi hui (external monitor par ye kaam nahi karta): {err[:150]}"
        return f"Brightness {level}% kar di."
    except Exception as e:
        return f"Brightness error: {e}"


# ---------------------------------------------------------------------------
# Power
# ---------------------------------------------------------------------------
@tool(category="system", label="Lock screen")
def lock_screen() -> str:
    """Lock the Windows session (Win+L)."""
    if not config.IS_WINDOWS:
        return "Sirf Windows par."
    ctypes.windll.user32.LockWorkStation()  # type: ignore[attr-defined]
    return "Screen lock kar di."


@tool(category="system", dangerous=True, label="Power action")
def system_power(action: str, delay_seconds: int = 30, confirmed: bool = False) -> str:
    """
    Power control: action = sleep | shutdown | restart | hibernate | logoff | cancel.
    shutdown/restart wait delay_seconds (so it can be cancelled with action='cancel'). Everything except
    'cancel' needs confirmation: confirmed=False first, then confirmed=True (same arguments) after user says yes.
    """
    a = (action or "").lower().strip()
    if a not in ("sleep", "shutdown", "restart", "hibernate", "logoff", "cancel"):
        return "action: sleep | shutdown | restart | hibernate | logoff | cancel"
    if not config.IS_WINDOWS:
        return "Sirf Windows par."
    if a == "cancel":
        subprocess.run(["shutdown", "/a"], capture_output=True, creationflags=CREATE_NO_WINDOW)
        return "Pending shutdown/restart cancel kar diya (agar koi tha)."
    delay = max(5, min(int(delay_seconds or 30), 600))
    gate = safety.confirm_gate("system_power", {"action": a, "delay": delay}, confirmed,
                               f"PC ko {a} karun? ({'%d second baad' % delay if a in ('shutdown', 'restart') else 'turant'}) "
                               "Khula hua kaam save kar lo.")
    if gate:
        return gate
    if a == "sleep":
        subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], creationflags=CREATE_NO_WINDOW)
    elif a == "hibernate":
        subprocess.Popen(["shutdown", "/h"], creationflags=CREATE_NO_WINDOW)
    elif a == "logoff":
        subprocess.Popen(["shutdown", "/l"], creationflags=CREATE_NO_WINDOW)
    elif a == "shutdown":
        subprocess.Popen(["shutdown", "/s", "/t", str(delay)], creationflags=CREATE_NO_WINDOW)
        return f"PC {delay} second mein shutdown hoga. Rokna ho to 'shutdown cancel' bolo."
    elif a == "restart":
        subprocess.Popen(["shutdown", "/r", "/t", str(delay)], creationflags=CREATE_NO_WINDOW)
        return f"PC {delay} second mein restart hoga. Rokna ho to 'restart cancel' bolo."
    return f"{a} kar raha hoon."


# ---------------------------------------------------------------------------
# Clipboard / theme / recycle bin
# ---------------------------------------------------------------------------
@tool(category="system", untrusted="clipboard", label="Read clipboard")
def clipboard_read() -> str:
    """Return the text currently on the Windows clipboard."""
    try:
        rc, out, err = run_ps("Get-Clipboard -Raw", timeout=10)
        return out if out else "Clipboard khaali hai (ya usme text nahi hai)."
    except Exception as e:
        return f"Clipboard padh nahi paya: {e}"


@tool(category="system", label="Set clipboard")
def clipboard_write(text: str) -> str:
    """Put text on the Windows clipboard so the user can paste it anywhere."""
    try:
        run_ps(f"Set-Clipboard -Value {ps_quote(text)}", timeout=10)
        return f"Clipboard par copy kar diya ({len(text)} chars)."
    except Exception as e:
        return f"Clipboard set nahi hua: {e}"


@tool(category="system", label="Dark mode")
def set_dark_mode(enabled: bool = True) -> str:
    """Switch Windows between dark mode (True) and light mode (False)."""
    if not config.IS_WINDOWS:
        return "Sirf Windows par."
    import winreg
    val = 0 if enabled else 1
    key = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, "AppsUseLightTheme", 0, winreg.REG_DWORD, val)
        winreg.SetValueEx(k, "SystemUsesLightTheme", 0, winreg.REG_DWORD, val)
    return "Dark mode ON kar diya." if enabled else "Light mode ON kar diya."


@tool(category="system", dangerous=True, label="Empty Recycle Bin")
def empty_recycle_bin(confirmed: bool = False) -> str:
    """
    Permanently empty the Recycle Bin. Needs confirmation: confirmed=False first, then confirmed=True
    after the user says yes.
    """
    gate = safety.confirm_gate("empty_recycle_bin", {}, confirmed,
                               "Recycle Bin ki saari files hamesha ke liye delete kar dun? Wapas nahi aayengi.")
    if gate:
        return gate
    try:
        run_ps("Clear-RecycleBin -Force -ErrorAction SilentlyContinue", timeout=60)
        return "Recycle Bin khaali kar diya."
    except Exception as e:
        return f"Recycle Bin khaali nahi hua: {e}"
