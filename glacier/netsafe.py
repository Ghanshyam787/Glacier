"""
Glacier - safe networking helpers
SSRF protection (private/localhost/metadata IPs blocked, har redirect hop pe check),
size-capped downloads, aur HTML -> clean text.
"""

import ipaddress
import re
import socket
from urllib.parse import urljoin, urlparse

try:
    import requests
except ImportError:  # doctor.py will report this
    requests = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Glacier/4.0 (+personal assistant)"
MAX_BYTES = 2_000_000
BLOCKED_HOSTS = {"localhost", "metadata.google.internal", "metadata"}


def ssrf_check(url: str):
    """None agar safe, warna reason string."""
    try:
        p = urlparse(url)
    except Exception:
        return "URL samajh nahi aaya."
    if p.scheme not in ("http", "https"):
        return "Sirf http/https URLs allowed hain."
    if p.username or p.password:
        return "URL mein username/password allowed nahi."
    host = (p.hostname or "").lower()
    if not host or host in BLOCKED_HOSTS or host.endswith(".local") or host.endswith(".internal"):
        return "Local/internal addresses blocked hain (SSRF protection)."
    try:
        infos = socket.getaddrinfo(host, p.port or (443 if p.scheme == "https" else 80), proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        return f"'{host}' resolve nahi hua (internet ya URL check karo)."
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                or ip.is_multicast or ip.is_unspecified):
            return "Ye address private/local network ka hai - blocked (SSRF protection)."
    return None


def safe_request(method: str, url: str, headers=None, data=None, timeout=15, max_redirects=5):
    """Returns (response, error). Manual redirects so har hop SSRF-checked ho."""
    if requests is None:
        return None, "requests library install nahi hai (pip install requests)."
    hdrs = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    hdrs.update(headers or {})
    current = url
    for _ in range(max_redirects + 1):
        err = ssrf_check(current)
        if err:
            return None, err
        try:
            r = requests.request(method, current, headers=hdrs, data=data, timeout=timeout,
                                 allow_redirects=False, stream=True)
        except requests.exceptions.RequestException as e:
            return None, f"Request fail hui: {type(e).__name__}: {str(e)[:150]}"
        if r.is_redirect or r.status_code in (301, 302, 303, 307, 308):
            loc = r.headers.get("Location")
            r.close()
            if not loc:
                return None, "Redirect mila par Location nahi tha."
            current = urljoin(current, loc)
            if method.upper() != "GET" and r.status_code in (301, 302, 303):
                method, data = "GET", None
            continue
        return r, None
    return None, "Bahut zyada redirects."


def read_limited(resp, max_bytes: int = MAX_BYTES) -> bytes:
    chunks, size = [], 0
    try:
        for chunk in resp.iter_content(chunk_size=16384):
            if not chunk:
                continue
            chunks.append(chunk)
            size += len(chunk)
            if size >= max_bytes:
                break
    finally:
        resp.close()
    return b"".join(chunks)[:max_bytes]


def decode_body(resp, raw: bytes) -> str:
    enc = resp.encoding or "utf-8"
    for candidate in (enc, "utf-8", "latin-1"):
        try:
            return raw.decode(candidate, errors="replace")
        except (LookupError, UnicodeDecodeError):
            continue
    return raw.decode("utf-8", errors="replace")


def html_to_text(html: str, max_chars: int = 12000) -> str:
    if not html:
        return ""
    if BeautifulSoup is not None:
        try:
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "noscript", "svg", "nav", "footer", "header", "form", "iframe"]):
                tag.decompose()
            title = soup.title.get_text(strip=True) if soup.title else ""
            main = soup.find("main") or soup.find("article") or soup.body or soup
            text = main.get_text("\n", strip=True)
            text = f"{title}\n{text}" if title else text
        except Exception:
            text = re.sub(r"<[^>]+>", " ", html)
    else:
        text = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
        text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()[:max_chars]


def fetch_text(url: str, max_chars: int = 12000, timeout: int = 15):
    """(text, error). HTML ko clean text bana ke deta hai; text/json jaisa hai waisa."""
    r, err = safe_request("GET", url, timeout=timeout)
    if err:
        return None, err
    if r.status_code >= 400:
        r.close()
        return None, f"Server ne HTTP {r.status_code} diya."
    ctype = (r.headers.get("Content-Type") or "").lower()
    raw = read_limited(r)
    body = decode_body(r, raw)
    if "html" in ctype or body.lstrip()[:15].lower().startswith(("<!doctype", "<html")):
        return html_to_text(body, max_chars), None
    if any(t in ctype for t in ("text", "json", "xml")) or not ctype:
        return body[:max_chars], None
    return None, f"Ye content type ({ctype}) text nahi hai."
