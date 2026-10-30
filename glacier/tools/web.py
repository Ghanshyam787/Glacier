"""
Glacier Tools: Web
search, open sites, fetch pages, HTTP requests, Wikipedia, YouTube, downloads.
Saara web content UNTRUSTED mark hota hai (prompt-injection protection) aur SSRF-safe network se aata hai.
"""

import json
import os
import re
import webbrowser
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import config
import netsafe
import safety
import winpaths
from registry import tool

SHORTCUTS = {
    "youtube": "https://www.youtube.com", "google": "https://www.google.com", "gmail": "https://mail.google.com",
    "github": "https://github.com", "whatsapp web": "https://web.whatsapp.com", "chatgpt": "https://chatgpt.com",
    "gemini": "https://gemini.google.com", "claude": "https://claude.ai", "linkedin": "https://www.linkedin.com",
    "twitter": "https://x.com", "x": "https://x.com", "instagram": "https://www.instagram.com",
    "facebook": "https://www.facebook.com", "maps": "https://maps.google.com", "drive": "https://drive.google.com",
    "netflix": "https://www.netflix.com", "amazon": "https://www.amazon.in", "flipkart": "https://www.flipkart.com",
}


def search_results(query: str, n: int = 6) -> list:
    """[{title, body, href}] - ddgs, warna DuckDuckGo HTML fallback. Raises RuntimeError agar dono fail."""
    results, err = None, ""
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS  # purana package name
        with DDGS() as d:
            results = list(d.text(query, max_results=n))
    except ImportError:
        err = "ddgs library install nahi hai (pip install ddgs)"
    except Exception as e:
        err = f"{type(e).__name__}: {str(e)[:120]}"
    if results:
        return results
    # fallback: DuckDuckGo HTML endpoint
    r, e2 = netsafe.safe_request("GET", "https://html.duckduckgo.com/html/?q=" + quote_plus(query), timeout=15)
    if r is not None and r.status_code < 400 and netsafe.BeautifulSoup is not None:
        html = netsafe.decode_body(r, netsafe.read_limited(r, 600_000))
        soup = netsafe.BeautifulSoup(html, "html.parser")
        out = []
        for res in soup.select(".result")[:n]:
            a = res.select_one("a.result__a")
            sn = res.select_one(".result__snippet")
            if not a:
                continue
            href = a.get("href", "")
            q = parse_qs(urlparse(href).query).get("uddg")
            if q:
                href = unquote(q[0])
            out.append({"title": a.get_text(strip=True), "body": sn.get_text(" ", strip=True) if sn else "", "href": href})
        if out:
            return out
    raise RuntimeError(err or e2 or "Koi result nahi mila")


@tool(category="web", untrusted="web search", label="Web search")
def web_search(query: str, max_results: int = 6) -> str:
    """Search the web (DuckDuckGo) and return the top results with title, snippet and link."""
    try:
        res = search_results(query, max(1, min(int(max_results or 6), 10)))
    except RuntimeError as e:
        return f"Search nahi ho paayi: {e}"
    if not res:
        return f"'{query}' ke liye kuchh nahi mila."
    return f"'{query}' ke results:\n" + "\n".join(
        f"{i}. {r.get('title', '')}\n   {(r.get('body') or '')[:200]}\n   {r.get('href', '')}" for i, r in enumerate(res, 1))


@tool(category="web", label="Open website")
def open_website(url: str) -> str:
    """Open a website in the default browser. Accepts a URL, a site name like 'youtube', or search words."""
    u = (url or "").strip()
    if not u:
        return "Kaunsi website kholni hai?"
    key = u.lower()
    if key in SHORTCUTS:
        u = SHORTCUTS[key]
    elif re.match(r"^[a-z][a-z0-9+.\-]*:", u) and not u.lower().startswith(("http://", "https://")):
        return "Sirf http/https links khol sakta hoon."
    elif not u.lower().startswith(("http://", "https://")):
        u = ("https://" + u) if ("." in u and " " not in u) else "https://www.google.com/search?q=" + quote_plus(u)
    webbrowser.open(u)
    return f"{u} browser mein khol diya."


@tool(category="web", untrusted="web page", label="Read web page")
def fetch_url(url: str, max_chars: int = 6000) -> str:
    """Download a web page and return its readable text (no browser needed)."""
    text, err = netsafe.fetch_text(url, max_chars=max(500, min(int(max_chars or 6000), 20000)))
    return err if err else (text or "(page khaali hai)")


@tool(category="web", dangerous=True, untrusted="http response", label="HTTP request")
def http_request(method: str, url: str, headers_json: str = "", body: str = "", confirmed: bool = False) -> str:
    """
    Make an HTTP request to a public URL. GET is free; POST/PUT/PATCH/DELETE change things on a server and need
    confirmation (confirmed=False first, then confirmed=True with the same arguments after the user says yes).
    headers_json is an optional JSON object string.
    """
    m = (method or "GET").upper()
    if m not in ("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"):
        return "Method galat hai."
    hdrs = {}
    if headers_json:
        try:
            hdrs = json.loads(headers_json)
        except Exception:
            return "headers_json valid JSON nahi hai."
    if m not in ("GET", "HEAD"):
        gate = safety.confirm_gate("http_request", {"m": m, "url": url, "body": body}, confirmed,
                                   f"{m} request bhejun?\n{url}\nBody: {body[:300]}")
        if gate:
            return gate
    r, err = netsafe.safe_request(m, url, headers=hdrs, data=body.encode("utf-8") if body else None, timeout=20)
    if err:
        return err
    raw = netsafe.read_limited(r, 400_000)
    return f"HTTP {r.status_code}\n" + netsafe.decode_body(r, raw)[:4000]


@tool(category="web", untrusted="Wikipedia", label="Wikipedia")
def wikipedia(topic: str, lang: str = "en") -> str:
    """Look up a topic on Wikipedia and return the summary (lang 'en' or 'hi')."""
    lang = lang if re.fullmatch(r"[a-z]{2,3}", lang or "") else "en"
    r, err = netsafe.safe_request("GET", f"https://{lang}.wikipedia.org/w/api.php?action=opensearch&limit=1&format=json&search={quote_plus(topic)}")
    if err:
        return err
    try:
        data = json.loads(netsafe.decode_body(r, netsafe.read_limited(r, 100_000)))
        title = data[1][0]
    except Exception:
        return f"Wikipedia par '{topic}' nahi mila."
    r2, err2 = netsafe.safe_request("GET", f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote_plus(title.replace(' ', '_'))}")
    if err2:
        return err2
    try:
        d = json.loads(netsafe.decode_body(r2, netsafe.read_limited(r2, 200_000)))
        return f"{d.get('title')}: {d.get('extract', '')}\n{d.get('content_urls', {}).get('desktop', {}).get('page', '')}"
    except Exception:
        return f"Wikipedia summary padh nahi paya for '{title}'."


@tool(category="web", label="Play on YouTube")
def youtube_play(query: str) -> str:
    """Find the best YouTube video for the query and open it in the browser."""
    r, err = netsafe.safe_request("GET", "https://www.youtube.com/results?search_query=" + quote_plus(query),
                                  headers={"Accept-Language": "en-IN,en;q=0.9"})
    vid = None
    if r is not None and r.status_code < 400:
        html = netsafe.decode_body(r, netsafe.read_limited(r, 1_500_000))
        m = re.search(r'"videoId":"([\w-]{11})"', html)
        vid = m.group(1) if m else None
    if vid:
        url = f"https://www.youtube.com/watch?v={vid}"
        webbrowser.open(url)
        return f"YouTube par chala diya: {url}"
    url = "https://www.youtube.com/results?search_query=" + quote_plus(query)
    webbrowser.open(url)
    return f"Exact video nahi mila, YouTube search khol diya: {url}"


@tool(category="web", dangerous=True, label="Download file")
def download_file(url: str, filename: str = "", confirmed: bool = False) -> str:
    """
    Download a file from a public URL into the Downloads folder (never overwrites, max 500 MB). Needs
    confirmation: confirmed=False first, then confirmed=True (same arguments) after the user says yes.
    """
    err = netsafe.ssrf_check(url)
    if err:
        return err
    name = filename or os.path.basename(urlparse(url).path) or "download"
    name = re.sub(r'[\\/:*?"<>|]', "_", name)[:120] or "download"
    gate = safety.confirm_gate("download_file", {"url": url, "name": name}, confirmed,
                               f"Ye file Downloads mein download karun?\n{url}\nNaam: {name}")
    if gate:
        return gate
    dest = os.path.join(winpaths.get_downloads(), name)
    base, ext = os.path.splitext(dest)
    i = 2
    while os.path.exists(dest):
        dest = f"{base} ({i}){ext}"
        i += 1
    r, err = netsafe.safe_request("GET", url, timeout=30)
    if err:
        return err
    if r.status_code >= 400:
        return f"Server ne HTTP {r.status_code} diya."
    size, limit = 0, 500 * 1024 * 1024
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    try:
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                size += len(chunk)
                if size > limit:
                    raise RuntimeError("500 MB limit cross ho gayi")
                f.write(chunk)
    except Exception as e:
        try:
            os.remove(dest)
        except OSError:
            pass
        return f"Download fail: {e}"
    finally:
        r.close()
    return f"Download ho gaya ({size / 1024 / 1024:.1f} MB): {dest}"
