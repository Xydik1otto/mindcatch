"""SQLite storage layer. All data stays local (single file)."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone

DEFAULT_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mindcatch.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL CHECK (type IN ('task','note','reminder')),
    text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'inbox',
    remind_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def get_conn() -> sqlite3.Connection:
    path = os.environ.get("MINDCATCH_DB", DEFAULT_DB)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Add columns introduced after the MVP schema to existing databases."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(items)").fetchall()}
    additions = {
        "due_date": "TEXT",
        "recurrence": "TEXT",
        "body": "TEXT",
        "estimate_minutes": "INTEGER",
    }
    for name, decl in additions.items():
        if name not in cols:
            conn.execute(f"ALTER TABLE items ADD COLUMN {name} {decl}")
    conn.execute("""CREATE TABLE IF NOT EXISTS time_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL REFERENCES items(id),
        started_at TEXT NOT NULL,
        ended_at TEXT,
        minutes INTEGER
    )""")
    conn.commit()


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()
    _migrate(conn)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_item(conn: sqlite3.Connection, text: str, type_: str,
                remind_at: str | None = None, status: str = "inbox",
                due_date: str | None = None) -> dict:
    cur = conn.execute(
        "INSERT INTO items (type, text, status, remind_at, due_date, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (type_, text, status, remind_at, due_date, now_iso(), now_iso()),
    )
    conn.commit()
    return get_item(conn, cur.lastrowid)


def get_item(conn: sqlite3.Connection, item_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    return dict(row) if row else None


def list_items(conn: sqlite3.Connection, status: str | None = None) -> list[dict]:
    if status:
        rows = conn.execute(
            "SELECT * FROM items WHERE status = ? ORDER BY id", (status,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM items ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def update_status(conn: sqlite3.Connection, item_id: int, status: str) -> dict | None:
    conn.execute("UPDATE items SET status = ?, updated_at = ? WHERE id = ?",
                 (status, now_iso(), item_id))
    conn.commit()
    return get_item(conn, item_id)


def update_fields(conn: sqlite3.Connection, item_id: int, **fields) -> dict | None:
    """Generic partial update (recurrence, body, estimate_minutes, ...)."""
    if not fields:
        return get_item(conn, item_id)
    cols = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE items SET {cols}, updated_at = ? WHERE id = ?",
                 (*fields.values(), now_iso(), item_id))
    conn.commit()
    return get_item(conn, item_id)


def export_all(conn: sqlite3.Connection) -> str:
    items = list_items(conn)
    return json.dumps({"exported_at": now_iso(), "items": items},
                      ensure_ascii=False, indent=2)
