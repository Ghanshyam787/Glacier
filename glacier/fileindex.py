"""
Glacier - File index (instant search)
Poore C:/D: ka naam-index SQLite mein (background thread, kam CPU). find_files isse milliseconds mein jawab deta hai.
Index sirf NAAM/size/date rakhta hai - file ka content nahi. System/secret folders skip hote hain.
"""

import os
import threading
import time

import config
import db
import safety

SKIP_DIR_NAMES = {
    "node_modules", ".git", "__pycache__", "site-packages", ".venv", "venv", "$recycle.bin", "windows.old",
    ".cache", "cache", "code cache", "gpucache", ".gradle", ".m2", ".npm", ".nuget", ".cargo", "temp", "tmp",
    "system volume information", "winsxs",
}

_build_lock = threading.Lock()
_state = {"running": False, "count": 0, "last_built": 0.0, "error": ""}


def state() -> dict:
    s = dict(_state)
    try:
        s["last_built"] = float(db.kv_get("index_built", "0") or 0)
        row = db.query_one("SELECT COUNT(*) AS n FROM files")
        s["rows"] = row["n"] if row else 0
    except Exception:
        s["rows"] = 0
    return s


def is_ready() -> bool:
    return state().get("rows", 0) > 1000 or float(db.kv_get("index_built", "0") or 0) > 0


def rebuild_index(max_seconds: int = 900) -> int:
    """Poora index dobara banao. Returns rows. Ek time pe ek hi build."""
    if not _build_lock.acquire(blocking=False):
        return -1
    _state.update(running=True, count=0, error="")
    started = time.time()
    total = 0
    try:
        db.execute("DROP TABLE IF EXISTS files_new")
        db.execute("CREATE TABLE files_new(path TEXT PRIMARY KEY, lname TEXT, is_dir INTEGER, size INTEGER, mtime REAL)")
        batch = []

        def flush():
            nonlocal batch, total
            if batch:
                db.executemany("INSERT OR IGNORE INTO files_new(path,lname,is_dir,size,mtime) VALUES(?,?,?,?,?)", batch)
                total += len(batch)
                _state["count"] = total
                batch = []

        for root_dir in config.SEARCH_DRIVES:
            stack = [root_dir]
            while stack:
                if time.time() - started > max_seconds:
                    _state["error"] = "time limit"
                    stack.clear()
                    break
                cur = stack.pop()
                try:
                    with os.scandir(cur) as it:
                        for entry in it:
                            try:
                                name = entry.name
                                is_dir = entry.is_dir(follow_symlinks=False)
                                if is_dir:
                                    if name.lower() in SKIP_DIR_NAMES or safety.is_blocked_path(entry.path):
                                        continue
                                    stack.append(entry.path)
                                    st = entry.stat(follow_symlinks=False)
                                    batch.append((entry.path, name.lower(), 1, 0, st.st_mtime))
                                else:
                                    st = entry.stat(follow_symlinks=False)
                                    batch.append((entry.path, name.lower(), 0, st.st_size, st.st_mtime))
                            except OSError:
                                continue
                except (PermissionError, FileNotFoundError, NotADirectoryError, OSError):
                    continue
                if len(batch) >= 4000:
                    flush()
                    time.sleep(0.01)  # CPU ko saans lene do
        flush()
        with db._write_lock:
            c = db.conn()
            c.execute("DROP TABLE IF EXISTS files")
            c.execute("ALTER TABLE files_new RENAME TO files")
            c.execute("CREATE INDEX IF NOT EXISTS idx_files_lname ON files(lname)")
            c.commit()
        db.kv_set("index_built", str(time.time()))
        return total
    except Exception as e:
        _state["error"] = f"{type(e).__name__}: {e}"
        return -2
    finally:
        _state["running"] = False
        _build_lock.release()


def start_background(delay: int = 20, refresh_hours: int = 12):
    """App start ke kuch second baad index banao, phir har refresh_hours pe."""
    def loop():
        time.sleep(delay)
        while True:
            try:
                last = float(db.kv_get("index_built", "0") or 0)
            except Exception:
                last = 0
            if time.time() - last > refresh_hours * 3600:
                rebuild_index()
            time.sleep(1800)
    threading.Thread(target=loop, daemon=True, name="glacier-indexer").start()


def search(tokens: list, kind: str = "any", ext: str = "", limit: int = 80, root: str = "") -> list:
    """Index mein AND-search. Returns rows (path,is_dir,size,mtime)."""
    where, params = [], []
    for t in tokens:
        where.append("lname LIKE ? ESCAPE '\\'")
        params.append("%" + t.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%")
    if kind == "file":
        where.append("is_dir=0")
    elif kind == "folder":
        where.append("is_dir=1")
    if ext:
        e = ext.lower().lstrip(".")
        where.append("lname LIKE ?")
        params.append(f"%.{e}")
    if root:
        where.append("path LIKE ?")
        params.append(root.rstrip("\\/") + "%")
    sql = "SELECT path,is_dir,size,mtime FROM files"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY mtime DESC LIMIT ?"
    params.append(limit)
    try:
        return db.query(sql, params)
    except Exception:
        return []
