"""
Glacier - Notifications
Ek jagah se: bolke batao + dashboard pe dikhao + Windows toast + Telegram (phone).
Sinks runtime pe register hote hain (voice, telegram), isliye ye module kisi se import-cycle nahi banata.
"""

import threading

import config
import events
from winutil import run_ps, ps_quote

_sinks = {}   # name -> (kind, fn)   kind: "speak" | "remote"
_lock = threading.Lock()


def register_sink(name: str, kind: str, fn):
    with _lock:
        _sinks[name] = (kind, fn)


def _toast(title: str, text: str):
    if not config.IS_WINDOWS:
        return
    script = (
        "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null;"
        "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null;"
        "$t = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
        f"$n = $t.GetElementsByTagName('text'); $n.Item(0).AppendChild($t.CreateTextNode({ps_quote(title)})) > $null;"
        f"$n.Item(1).AppendChild($t.CreateTextNode({ps_quote(text[:220])})) > $null;"
        "$toast = [Windows.UI.Notifications.ToastNotification]::new($t);"
        "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("
        "'{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe').Show($toast)"
    )
    try:
        run_ps(script, timeout=15)
    except Exception:
        pass


def notify(text: str, title: str = None, speak: bool = True, toast: bool = True, remote: bool = True):
    """Background-safe: kabhi exception nahi uthata."""
    title = title or config.ASSISTANT_NAME
    events.publish("notify", title=title, text=text)
    with _lock:
        sinks = list(_sinks.values())
    for kind, fn in sinks:
        if (kind == "speak" and not speak) or (kind == "remote" and not remote):
            continue
        threading.Thread(target=_safe, args=(fn, text), daemon=True).start()
    if toast:
        threading.Thread(target=_toast, args=(title, text), daemon=True).start()


def _safe(fn, text):
    try:
        fn(text)
    except Exception:
        pass
