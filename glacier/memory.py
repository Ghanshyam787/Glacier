"""
Glacier - Memory
================
1. Facts      : user ke baare mein permanent baatein ("mera naam...", "mujhe ... pasand hai")
2. Messages   : chat history disk pe - restart ke baad bhi context yaad
3. Knowledge  : tumhare documents ka local search index (SQLite FTS5 / BM25) - koi API nahi lagti
"""

import os
import re
import time

import db
import docreader

# ---------------------------------------------------------------- facts
_STOP = {"the", "a", "an", "is", "are", "of", "to", "my", "me", "i", "mera", "meri", "mere", "hai", "ka",
         "ki", "ke", "ko", "se", "me", "mein", "aur", "and", "or", "in", "on", "for", "kya", "tum"}


def _words(text: str) -> set:
    return {w for w in re.findall(r"\w+", (text or "").lower()) if len(w) > 1 and w not in _STOP}


def add_fact(text: str, tags: str = "") -> str:
    text = " ".join((text or "").split())[:500]
    if len(text) < 3:
        return "empty"
    now = time.time()
    existing = db.query_one("SELECT id FROM facts WHERE text = ?", (text,))
    if existing:
        db.execute("UPDATE facts SET updated=?, tags=? WHERE id=?", (now, tags, existing["id"]))
        return "exists"
    db.execute("INSERT INTO facts(text,tags,created,updated) VALUES(?,?,?,?)", (text, tags, now, now))
    return "added"


def search_facts(query: str, limit: int = 8) -> list:
    qw = _words(query)
    rows = db.query("SELECT id,text,tags FROM facts ORDER BY updated DESC")
    if not qw:
        return [dict(r) for r in rows[:limit]]
    scored = []
    for r in rows:
        overlap = len(qw & _words(r["text"] + " " + (r["tags"] or "")))
        if overlap or any(q in r["text"].lower() for q in qw):
            scored.append((overlap, r))
    scored.sort(key=lambda x: -x[0])
    return [dict(r) for _, r in scored[:limit]]


def delete_facts(query: str) -> int:
    """Fact id ya matching text se delete. Returns count."""
    query = (query or "").strip()
    if query.isdigit():
        cur = db.execute("DELETE FROM facts WHERE id=?", (int(query),))
        return cur.rowcount
    hits = search_facts(query, limit=3)
    q = query.lower()
    exact = [h for h in hits if q in h["text"].lower()]
    n = 0
    for h in (exact or hits[:1]):
        n += db.execute("DELETE FROM facts WHERE id=?", (h["id"],)).rowcount
    return n


def all_facts(limit: int = 80) -> list:
    return [dict(r) for r in db.query("SELECT id,text,tags FROM facts ORDER BY updated DESC LIMIT ?", (limit,))]


def profile_block(max_facts: int = 40) -> str:
    facts = all_facts(max_facts)
    if not facts:
        return ""
    return "\n".join(f"- {f['text']}" for f in facts)


# ---------------------------------------------------------------- messages
def log_message(session: str, role: str, text: str):
    if not text:
        return
    db.execute("INSERT INTO messages(session,role,text,ts) VALUES(?,?,?,?)", (session, role, text[:4000], time.time()))
    db.execute("DELETE FROM messages WHERE session=? AND id <= (SELECT MAX(id) FROM messages WHERE session=?) - 400",
               (session, session))


def recent_messages(session: str, limit: int = 12) -> list:
    rows = db.query("SELECT role,text FROM messages WHERE session=? ORDER BY id DESC LIMIT ?", (session, limit))
    return [(r["role"], r["text"]) for r in reversed(rows)]


def clear_messages(session: str):
    db.execute("DELETE FROM messages WHERE session=?", (session,))


# ---------------------------------------------------------------- knowledge base
CHUNK = 1200
OVERLAP = 150
SKIP_DIRS = {"node_modules", ".git", "__pycache__", "site-packages", ".venv", "venv", "$recycle.bin"}


def _chunks(text: str):
    text = re.sub(r"\n{3,}", "\n\n", text)
    i = 0
    while i < len(text):
        yield text[i:i + CHUNK]
        i += CHUNK - OVERLAP


def index_file(path: str) -> int:
    """File ko knowledge base mein daalo. Returns chunk count (0 = skipped)."""
    ext = os.path.splitext(path)[1].lower()
    if ext not in docreader.INDEXABLE_EXTS:
        return 0
    try:
        st = os.stat(path)
    except OSError:
        return 0
    row = db.query_one("SELECT mtime,size FROM kfiles WHERE path=?", (path,))
    if row and abs(row["mtime"] - st.st_mtime) < 1 and row["size"] == st.st_size:
        return -1  # unchanged
    text, err = docreader.read_text(path, max_chars=400_000)
    if err or not text:
        return 0
    chunks = list(_chunks(text))[:400]
    db.execute("DELETE FROM knowledge WHERE path=?", (path,))
    db.executemany("INSERT INTO knowledge(text,path,chunk) VALUES(?,?,?)",
                   [(c, path, i) for i, c in enumerate(chunks)])
    db.execute("INSERT OR REPLACE INTO kfiles(path,mtime,size,chunks) VALUES(?,?,?,?)",
               (path, st.st_mtime, st.st_size, len(chunks)))
    return len(chunks)


def index_folder(folder: str, max_files: int = 1500, is_allowed=None, max_seconds: int = 90) -> dict:
    stats = {"indexed": 0, "unchanged": 0, "skipped": 0, "chunks": 0}
    if not db.has_fts():
        stats["error"] = "SQLite FTS5 available nahi hai."
        return stats
    seen = 0
    deadline = time.time() + max_seconds
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS and not d.startswith(".")]
        if is_allowed and not is_allowed(root):
            dirs[:] = []
            continue
        for fn in files:
            seen += 1
            if seen > max_files or time.time() > deadline:
                stats["truncated"] = True
                return stats
            full = os.path.join(root, fn)
            if is_allowed and not is_allowed(full):
                stats["skipped"] += 1
                continue
            n = index_file(full)
            if n > 0:
                stats["indexed"] += 1
                stats["chunks"] += n
            elif n == -1:
                stats["unchanged"] += 1
            else:
                stats["skipped"] += 1
    return stats


def _fts_query(q: str) -> str:
    toks = [t for t in re.findall(r"\w+", q.lower(), re.UNICODE) if len(t) > 1 and t not in _STOP][:12]
    return " OR ".join(f'"{t}"' for t in toks)


def search_knowledge(query: str, limit: int = 5) -> list:
    if not db.has_fts():
        return []
    fq = _fts_query(query)
    if not fq:
        return []
    rows = db.query(
        "SELECT path, chunk, snippet(knowledge, 0, '[', ']', ' … ', 24) AS snip, bm25(knowledge) AS score "
        "FROM knowledge WHERE knowledge MATCH ? ORDER BY score LIMIT ?", (fq, limit))
    return [dict(r) for r in rows]


def knowledge_stats() -> dict:
    r = db.query_one("SELECT COUNT(*) AS n, COALESCE(SUM(chunks),0) AS c FROM kfiles")
    return {"files": r["n"], "chunks": r["c"]}


def forget_knowledge(path_prefix: str) -> int:
    rows = db.query("SELECT path FROM kfiles WHERE path LIKE ?", (path_prefix.replace("%", "") + "%",))
    for r in rows:
        db.execute("DELETE FROM knowledge WHERE path=?", (r["path"],))
        db.execute("DELETE FROM kfiles WHERE path=?", (r["path"],))
    return len(rows)
