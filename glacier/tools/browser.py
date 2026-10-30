"""
Glacier Tools: Browser automation (Playwright)
==============================================
Ek alag browser window (apna persistent profile: data/browser_profile) - ek baar kisi site pe login kar lo,
Glacier use dobara use kar sakta hai. Tumhare normal Chrome profile ko touch nahi karta.
Chrome/Edge installed ho to wahi use hota hai (alag download nahi). Warna: python -m playwright install chromium

Playwright ek hi thread se chalna chahiye, isliye ek dedicated worker thread hai.
"""

import os
import queue
import re
import threading
from concurrent.futures import Future

import config
import imgutil
import safety
from registry import tool

_RISKY_CLICK = re.compile(
    r"\b(pay|buy|purchase|order|checkout|place order|delete|remove|confirm|transfer|send money|donate|subscribe|"
    r"unsubscribe|post|publish|submit|sign out|log out|deactivate|cancel (?:order|subscription))\b", re.I)
_SENSITIVE_PAGE = re.compile(r"(pay|checkout|billing|bank|login|signin|sign-in|account|password|upi|card)", re.I)


class _Worker(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True, name="glacier-browser")
        self.q = queue.Queue()
        self.pw = None
        self.ctx = None
        self.page = None
        self.ready = threading.Event()
        self.start_error = None

    def run(self):
        try:
            from playwright.sync_api import sync_playwright
            self.pw = sync_playwright().start()
        except Exception as e:
            self.start_error = ("Playwright install nahi hai. Terminal mein chalao:\n"
                                "python -m pip install playwright  (aur agar Chrome/Edge nahi hai to: "
                                f"python -m playwright install chromium)\n[{type(e).__name__}: {e}]")
        self.ready.set()
        if self.start_error:
            return
        while True:
            item = self.q.get()
            if item is None:
                break
            fn, args, fut = item
            try:
                fut.set_result(fn(self, *args))
            except Exception as e:
                fut.set_exception(e)
        try:
            if self.ctx:
                self.ctx.close()
            self.pw.stop()
        except Exception:
            pass

    def call(self, fn, *args, timeout=75):
        if not self.ready.wait(20):
            raise RuntimeError("Browser worker start nahi hua.")
        if self.start_error:
            raise RuntimeError(self.start_error)
        fut = Future()
        self.q.put((fn, args, fut))
        return fut.result(timeout)


_worker = None
_wlock = threading.Lock()


def _get_worker() -> _Worker:
    global _worker
    with _wlock:
        if _worker is None or not _worker.is_alive():
            _worker = _Worker()
            _worker.start()
        return _worker


def _run(fn, *args, timeout=75):
    return _get_worker().call(fn, *args, timeout=timeout)


# ---- runs INSIDE the worker thread --------------------------------------------------------------
def _ensure_page(w: _Worker):
    if w.ctx is not None:
        try:
            w.ctx.pages  # noqa  (raises if the user closed the browser)
        except Exception:
            w.ctx = w.page = None
    if w.ctx is None:
        profile = os.path.join(config.DATA_DIR, "browser_profile")
        os.makedirs(profile, exist_ok=True)
        last = None
        channels = [c for c in (config.BROWSER_CHANNEL, "msedge", "chrome", None) if c != "chromium"]
        seen = set()
        for ch in channels:
            if ch in seen:
                continue
            seen.add(ch)
            try:
                kwargs = dict(user_data_dir=profile, headless=config.BROWSER_HEADLESS, no_viewport=True,
                              args=["--start-maximized", "--disable-blink-features=AutomationControlled"])
                if ch:
                    kwargs["channel"] = ch
                w.ctx = w.pw.chromium.launch_persistent_context(**kwargs)
                break
            except Exception as e:
                last = e
        if w.ctx is None:
            raise RuntimeError(f"Browser start nahi hua ({last}). Chrome/Edge install karo ya: "
                               "python -m playwright install chromium")
    pages = [p for p in w.ctx.pages if not p.is_closed()]
    if w.page is None or w.page.is_closed():
        w.page = pages[-1] if pages else w.ctx.new_page()
    return w.page


def _locate(page, target: str):
    """Visible element dhundo: css=..., text, role button/link, label, placeholder."""
    t = target.strip()
    cands = []
    if t.lower().startswith("css="):
        cands.append(page.locator(t[4:]))
    elif t[:1] in "#.[" or re.match(r"^[a-z]+\[", t):
        cands.append(page.locator(t))
    cands += [page.get_by_role("button", name=t), page.get_by_role("link", name=t), page.get_by_label(t),
              page.get_by_placeholder(t), page.get_by_role("textbox", name=t), page.get_by_text(t, exact=True),
              page.get_by_text(t)]
    for loc in cands:
        try:
            if loc.count() > 0:
                first = loc.first
                if first.is_visible():
                    return first
        except Exception:
            continue
    return None


def _title_url(page) -> str:
    try:
        return f"{page.title()[:80]} - {page.url[:160]}"
    except Exception:
        return page.url


# ---- tools ----------------------------------------------------------------------------------------
@tool(category="browser", label="Browser: open")
def browser_open(url: str) -> str:
    """Open a URL in Glacier's automation browser (separate window with its own saved logins). Use browser_read afterwards to see the page."""
    u = (url or "").strip()
    if not re.match(r"^https?://", u, re.I):
        u = "https://" + u
    if not re.match(r"^https?://[^\s]+\.[^\s]+|^https?://localhost", u, re.I):
        return "URL sahi nahi lag raha."

    def go(w):
        page = _ensure_page(w)
        page.goto(u, wait_until="domcontentloaded", timeout=40000)
        try:
            page.wait_for_load_state("networkidle", timeout=6000)
        except Exception:
            pass
        return _title_url(page)
    try:
        return "Khul gaya: " + _run(go)
    except Exception as e:
        return f"Browser mein nahi khula: {str(e)[:250]}"


@tool(category="browser", untrusted="web page", label="Browser: read page")
def browser_read(max_chars: int = 5000) -> str:
    """Read the visible text of the current page in Glacier's browser."""
    def read(w):
        page = _ensure_page(w)
        txt = page.evaluate("() => document.body ? document.body.innerText : ''")
        return f"{_title_url(page)}\n{re.sub(chr(10) + '{3,}', chr(10) * 2, txt)[:max(500, min(int(max_chars or 5000), 15000))]}"
    try:
        return _run(read)
    except Exception as e:
        return f"Page padh nahi paya: {str(e)[:250]}"


@tool(category="browser", untrusted="web page", label="Browser: page structure")
def browser_snapshot(max_chars: int = 5000) -> str:
    """Accessibility snapshot of the page (buttons, links, inputs with their names) - use this to decide what to click/type."""
    def snap(w):
        page = _ensure_page(w)
        try:
            tree = page.locator("body").aria_snapshot()
        except Exception:
            tree = page.evaluate("() => Array.from(document.querySelectorAll('a,button,input,textarea,select'))"
                                 ".slice(0,80).map(e => (e.tagName+' '+(e.innerText||e.placeholder||e.name||e.ariaLabel||'')).trim()).join('\\n')")
        return f"{_title_url(page)}\n{tree[:max(500, min(int(max_chars or 5000), 15000))]}"
    try:
        return _run(snap)
    except Exception as e:
        return f"Snapshot nahi mila: {str(e)[:250]}"


@tool(category="browser", dangerous=True, label="Browser: click")
def browser_click(target: str, confirmed: bool = False) -> str:
    """
    Click a button/link/element by its visible text, label, or a CSS selector ('css=#submit'). Clicks that look
    irreversible (pay, buy, order, delete, confirm, submit, post, send ...) need confirmation: call with
    confirmed=False first, then confirmed=True (same arguments) after the user says yes.
    """
    if _RISKY_CLICK.search(target or ""):
        gate = safety.confirm_gate("browser_click", {"target": target}, confirmed,
                                   f"Browser mein '{target}' par click karun? Ye action wapas nahi ho sakta.")
        if gate:
            return gate

    def click(w):
        page = _ensure_page(w)
        el = _locate(page, target)
        if el is None:
            return f"'{target}' page par nahi mila. browser_snapshot se exact naam dekho."
        el.click(timeout=8000)
        try:
            page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        return "Click ho gaya. Ab: " + _title_url(page)
    try:
        return _run(click)
    except Exception as e:
        return f"Click nahi ho paya: {str(e)[:250]}"


@tool(category="browser", dangerous=True, label="Browser: type")
def browser_type(target: str, text: str, submit: bool = False, confirmed: bool = False) -> str:
    """
    Type text into an input field (found by label/placeholder/name/css). submit=True presses Enter afterwards.
    On login/payment/account pages, submitting needs confirmation (confirmed=False first, then True).
    """
    def pre(w):
        return _ensure_page(w).url
    try:
        url = _run(pre)
    except Exception as e:
        return f"Browser ready nahi: {str(e)[:200]}"
    if submit and (_SENSITIVE_PAGE.search(url) or _RISKY_CLICK.search(text or "")):
        gate = safety.confirm_gate("browser_type", {"target": target, "text": text, "url": url}, confirmed,
                                   f"'{target}' mein type karke Enter dabaun? Page: {url[:100]}")
        if gate:
            return gate

    def typ(w):
        page = _ensure_page(w)
        el = _locate(page, target)
        if el is None:
            return f"'{target}' field nahi mila. browser_snapshot se exact naam dekho."
        el.click(timeout=6000)
        el.fill(text, timeout=8000)
        if submit:
            el.press("Enter")
            try:
                page.wait_for_load_state("domcontentloaded", timeout=6000)
            except Exception:
                pass
        return f"Type kar diya{' + Enter' if submit else ''}. Ab: " + _title_url(page)
    try:
        return _run(typ)
    except Exception as e:
        return f"Type nahi ho paya: {str(e)[:250]}"


@tool(category="browser", label="Browser: press key")
def browser_press(key: str) -> str:
    """Press a key on the current page, e.g. 'Enter', 'Escape', 'PageDown', 'Control+a'."""
    def press(w):
        _ensure_page(w).keyboard.press(key)
        return f"Dabaya: {key}"
    try:
        return _run(press)
    except Exception as e:
        return f"Key nahi dabi: {str(e)[:200]}"


@tool(category="browser", label="Browser: scroll")
def browser_scroll(direction: str = "down", amount: int = 700) -> str:
    """Scroll the page: direction 'down' or 'up'."""
    def sc(w):
        dy = abs(int(amount or 700)) * (1 if direction.lower() != "up" else -1)
        _ensure_page(w).mouse.wheel(0, dy)
        return "Scroll kar diya."
    try:
        return _run(sc)
    except Exception as e:
        return f"Scroll nahi hua: {str(e)[:200]}"


@tool(category="browser", untrusted="web page", label="Browser: links")
def browser_links(contains: str = "", limit: int = 25) -> str:
    """List links on the current page (optionally only those whose text/URL contains a word)."""
    def links(w):
        page = _ensure_page(w)
        items = page.evaluate("() => Array.from(document.querySelectorAll('a[href]')).map(a => [a.innerText.trim().slice(0,80), a.href])")
        key = (contains or "").lower()
        out = [f"{t or '(no text)'} -> {h}" for t, h in items if h.startswith("http") and (not key or key in (t + h).lower())]
        return "\n".join(out[:max(1, min(int(limit or 25), 60))]) or "Koi link nahi mila."
    try:
        return _run(links)
    except Exception as e:
        return f"Links nahi mile: {str(e)[:200]}"


@tool(category="browser", label="Browser: tabs")
def browser_tabs(action: str = "list", index: int = 0, url: str = "") -> str:
    """Manage tabs: action = list | new (opens url) | switch (to index) | close (current tab) | back."""
    def tabs(w):
        page = _ensure_page(w)
        pages = [p for p in w.ctx.pages if not p.is_closed()]
        a = action.lower()
        if a == "list":
            return "\n".join(f"{i}: {p.title()[:60]} - {p.url[:90]}" + (" (current)" if p == page else "") for i, p in enumerate(pages))
        if a == "new":
            w.page = w.ctx.new_page()
            if url:
                w.page.goto(url if url.startswith("http") else "https://" + url, wait_until="domcontentloaded", timeout=40000)
            return "Naya tab: " + _title_url(w.page)
        if a == "switch":
            if 0 <= index < len(pages):
                w.page = pages[index]
                w.page.bring_to_front()
                return "Tab badla: " + _title_url(w.page)
            return "Is number ka tab nahi hai."
        if a == "close":
            page.close()
            rest = [p for p in w.ctx.pages if not p.is_closed()]
            w.page = rest[-1] if rest else None
            return "Tab band kiya."
        if a == "back":
            page.go_back(timeout=15000)
            return "Peeche gaya: " + _title_url(page)
        return "action: list | new | switch | close | back"
    try:
        return _run(tabs)
    except Exception as e:
        return f"Tab action fail: {str(e)[:200]}"


@tool(category="browser", label="Browser: screenshot")
def browser_screenshot() -> str:
    """Screenshot of the current page in Glacier's browser. Returns the file path (use describe_image to look at it)."""
    def shot(w):
        path = os.path.join(imgutil.screenshot_dir(), "browser_" + __import__("time").strftime("%Y%m%d_%H%M%S") + ".png")
        _ensure_page(w).screenshot(path=path, full_page=False)
        return path
    try:
        return f"Page screenshot: {_run(shot)}"
    except Exception as e:
        return f"Screenshot nahi hua: {str(e)[:200]}"


@tool(category="browser", label="Browser: close")
def browser_close() -> str:
    """Close Glacier's automation browser."""
    global _worker
    if _worker is None or not _worker.is_alive():
        return "Browser pehle se band hai."

    def close(w):
        if w.ctx:
            w.ctx.close()
        w.ctx = w.page = None
        return "Browser band kar diya."
    try:
        return _run(close)
    except Exception as e:
        return f"Band nahi hua: {str(e)[:200]}"
