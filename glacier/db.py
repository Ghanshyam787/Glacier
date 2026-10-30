"""
Glacier - local SQLite database (memory, reminders, notes, index, traces ...).
Ek hi file: data/glacier.db. Thread-safe: har thread ka apna connection, writes ek lock se.
"""

import sqlite3
import threading
import time

import config

_local = threading.local()
_write_lock = threading.RLock()
_init_lock = threading.Lock()
_initialised = False

SCHEMA = """
CREATE TABLE IF NOT EXISTS facts(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL UNIQUE COLLATE NOCASE,
    tags TEXT DEFAULT '',
    created REAL, updated REAL
);
CREATE TABLE IF NOT EXISTS messages(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session TEXT, role TEXT, text TEXT, ts REAL
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session, id);
CREATE TABLE IF NOT EXISTS activity(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL, label TEXT, text TEXT
);
CREATE TABLE IF NOT EXISTS reminders(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT, fire_at REAL, recur TEXT DEFAULT '', fired INTEGER DEFAULT 0, created REAL
);
CREATE TABLE IF NOT EXISTS tasks(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT, prompt TEXT, spec TEXT, next_run REAL, last_run REAL,
    enabled INTEGER DEFAULT 1, created REAL
);
CREATE TABLE IF NOT EXISTS watches(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT, keyword TEXT DEFAULT '', every_min INTEGER DEFAULT 30,
    last_check REAL DEFAULT 0, last_hash TEXT DEFAULT '', last_state TEXT DEFAULT '',
    enabled INTEGER DEFAULT 1, created REAL
);
CREATE TABLE IF NOT EXISTS todos(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT, done INTEGER DEFAULT 0, due TEXT DEFAULT '', created REAL, completed REAL
);
CREATE TABLE IF NOT EXISTS notes(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT, body TEXT, created REAL
);
CREATE TABLE IF NOT EXISTS calendar_events(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT, start REAL, end REAL, notes TEXT DEFAULT '', reminded INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS contacts(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT, phone TEXT DEFAULT '', email TEXT DEFAULT '', notes TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS traces(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL, session TEXT, user_text TEXT, reply TEXT, tools TEXT, model TEXT,
    latency REAL, calls INTEGER, rating INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS files(
    path TEXT PRIMARY KEY, lname TEXT, is_dir INTEGER, size INTEGER, mtime REAL
);
CREATE INDEX IF NOT EXISTS idx_files_lname ON files(lname);
CREATE TABLE IF NOT EXISTS kfiles(
    path TEXT PRIMARY KEY, mtime REAL, size INTEGER, chunks INTEGER
);
CREATE TABLE IF NOT EXISTS kv(
    key TEXT PRIMARY KEY, value TEXT
);
"""

FTS_SCHEMA = "CREATE VIRTUAL TABLE IF NOT EXISTS knowledge USING fts5(text, path UNINDEXED, chunk UNINDEXED)"

_fts_ok = None


def _connect() -> sqlite3.Connection:
    c = sqlite3.connect(config.DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    try:
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA synchronous=NORMAL")
    except sqlite3.DatabaseError:
        pass
    return c


def conn() -> sqlite3.Connection:
    global _initialised
    c = getattr(_local, "c", None)
    if c is None:
        c = _connect()
        _local.c = c
    if not _initialised:
        with _init_lock:
            if not _initialised:
                _init(c)
                _initialised = True
    return c


def _init(c: sqlite3.Connection):
    global _fts_ok
    c.executescript(SCHEMA)
    try:
        c.execute(FTS_SCHEMA)
        _fts_ok = True
    except sqlite3.OperationalError:
        _fts_ok = False
    c.commit()


def has_fts() -> bool:
    conn()
    return bool(_fts_ok)


def execute(sql: str, params=()):
    with _write_lock:
        c = conn()
        cur = c.execute(sql, params)
        c.commit()
        return cur


def executemany(sql: str, rows):
    with _write_lock:
        c = conn()
        c.executemany(sql, rows)
        c.commit()


def query(sql: str, params=()):
    return conn().execute(sql, params).fetchall()


def query_one(sql: str, params=()):
    return conn().execute(sql, params).fetchone()


def kv_get(key: str, default=None):
    row = query_one("SELECT value FROM kv WHERE key=?", (key,))
    return row["value"] if row else default


def kv_set(key: str, value: str):
    execute("INSERT INTO kv(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))


def now() -> float:
    return time.time()
