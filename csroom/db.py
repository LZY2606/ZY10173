import sqlite3
from contextlib import contextmanager

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    event_id      TEXT PRIMARY KEY,
    event_type    TEXT NOT NULL,
    boot_id       TEXT,
    seq           INTEGER,
    ts            REAL,
    payload       TEXT NOT NULL,
    content_hash  TEXT NOT NULL,
    recv_seq      INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS geometry_versions (
    version_id     TEXT PRIMARY KEY,
    geom_start     REAL NOT NULL,
    geom_end       REAL,
    model          TEXT NOT NULL,
    params_json    TEXT NOT NULL,
    length_unit    TEXT NOT NULL,
    load_unit      TEXT NOT NULL,
    note           TEXT,
    created_seq    INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS drafts (
    id            TEXT PRIMARY KEY,
    title         TEXT NOT NULL,
    base_version  TEXT,
    from_recv_seq INTEGER,
    input_set     TEXT NOT NULL DEFAULT 'live',
    input_revision INTEGER NOT NULL,
    params_json   TEXT NOT NULL,
    confirmed_json TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'open',
    sealed_version TEXT,
    created_seq   INTEGER NOT NULL,
    updated_seq   INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS draft_ops (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    draft_id    TEXT NOT NULL REFERENCES drafts(id),
    base_version INTEGER NOT NULL,
    new_version  INTEGER NOT NULL,
    op_type      TEXT NOT NULL,
    op_json      TEXT NOT NULL,
    client_note  TEXT,
    seq          INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS draft_exclusions (
    draft_id TEXT NOT NULL REFERENCES drafts(id),
    event_id TEXT NOT NULL,
    PRIMARY KEY (draft_id, event_id)
);

CREATE TABLE IF NOT EXISTS sealed_versions (
    version_id  TEXT PRIMARY KEY,
    draft_id    TEXT NOT NULL,
    version_no  INTEGER NOT NULL,
    title       TEXT NOT NULL,
    base_version TEXT,
    watermark_json TEXT NOT NULL,
    input_hash  TEXT NOT NULL,
    exclusions_json TEXT NOT NULL,
    params_json TEXT NOT NULL,
    result_json TEXT NOT NULL,
    summary_json TEXT NOT NULL,
    created_seq INTEGER NOT NULL,
    UNIQUE(draft_id, version_no)
);

CREATE TABLE IF NOT EXISTS audit_log (
    seq        INTEGER PRIMARY KEY AUTOINCREMENT,
    action     TEXT NOT NULL,
    entity     TEXT NOT NULL,
    entity_id  TEXT,
    detail_json TEXT,
    input_hash TEXT,
    entry_hash TEXT NOT NULL,
    prev_hash  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS idempotency (
    key        TEXT PRIMARY KEY,
    scope      TEXT NOT NULL,
    response_json TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    audit_seq  INTEGER,
    created_seq INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS seal_pending (
    draft_id    TEXT PRIMARY KEY,
    idem_key    TEXT,
    op_seq      INTEGER NOT NULL,
    input_hash  TEXT NOT NULL,
    created_seq INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS import_registry (
    bundle_hash TEXT PRIMARY KEY,
    imported_seq INTEGER NOT NULL
);
"""


def connect(db_path=None):
    path = str(db_path or DB_PATH)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(conn):
    conn.executescript(SCHEMA)
    conn.commit()


@contextmanager
def transaction(conn):
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def next_recv_seq(conn):
    row = conn.execute("SELECT COALESCE(MAX(recv_seq),0) AS m FROM events").fetchone()
    return row["m"] + 1


def next_audit_seq(conn):
    row = conn.execute("SELECT COALESCE(MAX(seq),0) AS m FROM audit_log").fetchone()
    return row["m"] + 1
