"""
Glacier - tiny in-process event bus.
Background threads (scheduler, monitors, Telegram...) publish events; the GUI,
tray etc. subscribe. Subscribers must never be able to break the publisher.
"""

import threading

_subscribers = []
_lock = threading.Lock()


def subscribe(fn):
    with _lock:
        if fn not in _subscribers:
            _subscribers.append(fn)


def unsubscribe(fn):
    with _lock:
        if fn in _subscribers:
            _subscribers.remove(fn)


def publish(kind: str, **payload):
    with _lock:
        subs = list(_subscribers)
    for fn in subs:
        try:
            fn(kind, payload)
        except Exception:
            pass
