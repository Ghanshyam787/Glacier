"""
Glacier - Offline docs (cppreference + MDN)
===========================================
Ek baar download hota hai (GitHub se, free), phir sab offline search hota hai.
  cppreference : PeterFeicht/cppreference-doc ka "html-book" release (C aur C++ reference)
  MDN          : mdn/content repo (HTML, CSS, JavaScript, Web APIs - sirf English markdown)
Index: SQLite (FTS5 ho to wahi, warna LIKE). Jagah: <data>/docs/docs.db
Download sirf neeche ki GitHub hosts se; size limit; kuch bhi execute nahi hota (sirf text padhte hain).
"""

import html.parser
import io
import os
import re
import sqlite3
import tarfile
import tempfile
import threading
import time
import zipfile
from urllib.parse import urlparse

import config

DOCS_DIR = os.path.join(config.DATA_DIR, "docs")
DB_FILE = os.path.join(DOCS_DIR, "docs.db")
ALLOWED_HOSTS = ("github.com", "githubusercontent.com")
MAX_DOWNLOAD = 450 * 1024 * 1024
MAX_BODY = 6000
MDN_URL = "https://codeload.github.com/mdn/content/zip/refs/heads/main"
CPPREF_API = "https://api.github.com/repos/PeterFeicht/cppreference-doc/releases/latest"

STATUS = {"state": "idle", "message": "", "started": 0.0}
_lock = threading.Lock()


def _set(state: str, msg: str):
    STATUS.update(state=state, message=msg)


# ------------------------------------------------------------------ db
def _connect():
    os.makedirs(DOCS_DIR, exist_ok=True)
    db = sqlite3.connect(DB_FILE)
    db.execute("CREATE TABLE IF NOT EXISTS docs(id INTEGER PRIMARY KEY, source TEXT, lang TEXT, title TEXT, path TEXT, body TEXT)")
    try:
        db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(title, body, content='docs', content_rowid='id')")
    except sqlite3.OperationalError:
        pass   # FTS5 nahi hai -> LIKE search chalega
    return db


def _has_fts(db) -> bool:
    return db.execute("SELECT name FROM sqlite_master WHERE name='docs_fts'").fetchone() is not None


def is_installed() -> bool:
    if not os.path.exists(DB_FILE):
        return False
    try:
        db = sqlite3.connect(DB_FILE)
        n = db.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
        db.close()
        return n > 0
    except sqlite3.Error:
        return False


def counts() -> dict:
    if not os.path.exists(DB_FILE):
        return {}
    try:
        db = sqlite3.connect(DB_FILE)
        out = dict(db.execute("SELECT source, COUNT(*) FROM docs GROUP BY source").fetchall())
        db.close()
        return out
    except sqlite3.Error:
        return {}


def _store(db, source: str, rows: list):
    db.execute("DELETE FROM docs WHERE source=?", (source,))
    db.executemany("INSERT INTO docs(source, lang, title, path, body) VALUES(?,?,?,?,?)", rows)
    if _has_fts(db):
        db.execute("INSERT INTO docs_fts(docs_fts) VALUES('rebuild')")
    db.commit()


# ------------------------------------------------------------------ text extraction
class _Text(html.parser.HTMLParser):
    SKIP = {"script", "style", "nav", "head", "noscript"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.title, self._skip, self._in_title, self._h1 = [], "", 0, False, False
        self.h1 = ""

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        elif tag in self.SKIP:
            self._skip += 1
        elif tag == "h1":
            self._h1 = True
        elif tag in ("p", "br", "tr", "li", "div", "pre", "h2", "h3", "h4"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag in self.SKIP and self._skip:
            self._skip -= 1
        elif tag == "h1":
            self._h1 = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif self._h1:
            self.h1 += data
        if not self._skip and not self._in_title:
            self.parts.append(data)


def html_to_text(src: str):
    p = _Text()
    try:
        p.feed(src)
    except Exception:
        pass
    text = re.sub(r"[ \t]+", " ", "".join(p.parts))
    text = re.sub(r"\n\s*\n+", "\n", text).strip()
    title = (p.h1 or p.title or "").strip()
    title = re.sub(r"\s*-\s*cppreference\.com\s*$", "", title).strip()
    return title, text[:MAX_BODY]


_FM = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def md_to_text(src: str):
    title = ""
    m = _FM.match(src)
    if m:
        t = re.search(r"^title:\s*(.+)$", m.group(1), re.M)
        title = t.group(1).strip().strip("\"'") if t else ""
        src = src[m.end():]
    src = re.sub(r"\{\{\s*([A-Za-z]+)(?:\(([^)]*)\))?\s*\}\}", lambda x: (x.group(2) or "").strip("\"' "), src)  # {{HTMLElement("div")}} -> div
    src = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", src)
    src = re.sub(r"\n{3,}", "\n\n", src).strip()
    return title, src[:MAX_BODY]


# ------------------------------------------------------------------ archive indexers (testable without network)
def index_cppreference_archive(path: str) -> int:
    """html-book zip ya tar(.xz/.gz) -> index. 'reference/en/c/' aur 'reference/en/cpp/' ke pages."""
    rows = []
    pat = re.compile(r"(?:^|/)reference/en/(c|cpp)/(.+\.html)$")

    def add(name: str, data: bytes):
        m = pat.search(name)
        if not m or name.endswith(("index.html",)) and m.group(2) == "index.html":
            return
        title, text = html_to_text(data.decode("utf-8", "ignore"))
        if title and len(text) > 80:
            rows.append(("cppreference", m.group(1), title, "reference/en/%s/%s" % (m.group(1), m.group(2)), text))

    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if n.endswith(".html") and pat.search(n):
                    add(n, z.read(n))
    else:
        with tarfile.open(path) as t:
            for mem in t:
                if mem.isfile() and mem.name.endswith(".html") and pat.search(mem.name):
                    f = t.extractfile(mem)
                    if f:
                        add(mem.name, f.read())
    db = _connect()
    _store(db, "cppreference", rows)
    db.close()
    return len(rows)


_MDN_LANG = (("files/en-us/web/html/", "html"), ("files/en-us/web/css/", "css"),
             ("files/en-us/web/javascript/", "js"), ("files/en-us/web/api/", "js"))


def index_mdn_archive(path: str) -> int:
    rows = []
    with zipfile.ZipFile(path) as z:
        for n in z.namelist():
            if not n.endswith("/index.md"):
                continue
            rel = n.split("/", 1)[-1].lower()           # zip root folder hata ke
            lang = next((l for pre, l in _MDN_LANG if rel.startswith(pre)), "")
            if not lang:
                continue
            title, text = md_to_text(z.read(n).decode("utf-8", "ignore"))
            if title and len(text) > 80:
                rows.append(("mdn", lang, title, rel, text))
    db = _connect()
    _store(db, "mdn", rows)
    db.close()
    return len(rows)


# ------------------------------------------------------------------ search
def _fts_query(query: str) -> str:
    words = [w for w in re.findall(r"[A-Za-z0-9_]+", query or "") if len(w) > 1]
    return " OR ".join('"%s"' % w for w in words[:8])


def search(query: str, lang: str = "", limit: int = 3) -> list:
    """[(title, source, path, text)] - lang: c | cpp | html | css | js | '' (sab)."""
    if not is_installed():
        return []
    langs = {"html": ("html", "css", "js"), "web": ("html", "css", "js")}.get(lang, (lang,) if lang else ())
    db = sqlite3.connect(DB_FILE)
    try:
        rows = []
        if _has_fts(db) and _fts_query(query):
            q = "SELECT d.title, d.source, d.path, d.body FROM docs_fts f JOIN docs d ON d.id=f.rowid WHERE docs_fts MATCH ?"
            args = [_fts_query(query)]
            if langs:
                q += " AND d.lang IN (%s)" % ",".join("?" * len(langs))
                args += list(langs)
            q += " ORDER BY bm25(docs_fts, 10.0, 1.0) LIMIT ?"
            args.append(limit)
            try:
                rows = db.execute(q, args).fetchall()
            except sqlite3.OperationalError:
                rows = []
        if not rows:
            words = [w for w in re.findall(r"[A-Za-z0-9_:]+", query or "") if len(w) > 1][:4]
            if words:
                q = "SELECT title, source, path, body FROM docs WHERE " + " AND ".join("(title LIKE ? OR body LIKE ?)" for _ in words)
                args = [x for w in words for x in ("%" + w + "%",) * 2]
                if langs:
                    q += " AND lang IN (%s)" % ",".join("?" * len(langs))
                    args += list(langs)
                q += " ORDER BY length(title) LIMIT ?"
                args.append(limit)
                rows = db.execute(q, args).fetchall()
        return rows
    finally:
        db.close()


# ------------------------------------------------------------------ download (sirf allowed GitHub hosts)
def _host_ok(url: str) -> bool:
    h = (urlparse(url).hostname or "").lower()
    return urlparse(url).scheme == "https" and any(h == a or h.endswith("." + a) for a in ALLOWED_HOSTS)


def _download(url: str, dest: str, label: str):
    import requests
    if not _host_ok(url):
        raise RuntimeError("Ye host allowed nahi hai: " + url)
    got = 0
    with requests.get(url, stream=True, timeout=30, headers={"User-Agent": "Glacier-docs"}) as r:
        r.raise_for_status()
        if not _host_ok(r.url):
            raise RuntimeError("Redirect allowed host par nahi gaya.")
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                got += len(chunk)
                if got > MAX_DOWNLOAD:
                    raise RuntimeError("Download bahut bada hai, rok diya.")
                f.write(chunk)
                _set("running", "%s download: %d MB" % (label, got // (1 << 20)))


def _install_cppreference(tmp: str) -> int:
    import requests
    _set("running", "cppreference ka latest release dhundh raha hoon...")
    r = requests.get(CPPREF_API, timeout=30, headers={"User-Agent": "Glacier-docs", "Accept": "application/vnd.github+json"})
    r.raise_for_status()
    assets = [a for a in r.json().get("assets", []) if re.search(r"html-book.*\.(zip|tar\.xz|tar\.gz|tar\.bz2)$", a.get("name", ""))]
    if not assets:
        raise RuntimeError("cppreference html-book release nahi mila.")
    a = assets[0]
    dest = os.path.join(tmp, a["name"])
    _download(a["browser_download_url"], dest, "cppreference")
    _set("running", "cppreference index ban raha hai...")
    return index_cppreference_archive(dest)


def _install_mdn(tmp: str) -> int:
    dest = os.path.join(tmp, "mdn.zip")
    _download(MDN_URL, dest, "MDN")
    _set("running", "MDN index ban raha hai (kuch minute)...")
    return index_mdn_archive(dest)


def install(which: str = "all") -> str:
    """Blocking. Background thread se call karo (start_install)."""
    which = (which or "all").lower()
    results, errors = [], []
    with tempfile.TemporaryDirectory() as tmp:
        for name, fn in (("cppreference", _install_cppreference), ("mdn", _install_mdn)):
            if which not in ("all", name):
                continue
            try:
                results.append("%s: %d pages" % (name, fn(tmp)))
            except Exception as e:
                errors.append("%s: %s" % (name, str(e)[:200]))
    msg = "; ".join(results) or "kuch install nahi hua"
    if errors:
        msg += " | ERRORS: " + "; ".join(errors)
    _set("error" if errors and not results else "done", msg)
    return msg


def start_install(which: str = "all") -> str:
    with _lock:
        if STATUS["state"] == "running":
            return "Pehle se chal raha hai: " + STATUS["message"]
        _set("running", "shuru ho raha hai...")
        STATUS["started"] = time.time()
        threading.Thread(target=lambda: install(which), daemon=True, name="docsync").start()
    return "Shuru ho gaya."
