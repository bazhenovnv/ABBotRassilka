from __future__ import annotations

import sqlite3

from config.settings import settings


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    full_name TEXT,
    is_subscribed INTEGER NOT NULL DEFAULT 1,
    is_blocked INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_message_at TEXT
);

CREATE TABLE IF NOT EXISTS cooldowns (
    user_id INTEGER PRIMARY KEY,
    until_ts INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS message_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    direction TEXT NOT NULL,
    content_type TEXT NOT NULL,
    text TEXT,
    telegram_message_id INTEGER,
    created_at TEXT NOT NULL
);
"""


def get_connection() -> sqlite3.Connection:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        _migrate_legacy_users(conn)
        conn.commit()


def _column_exists(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row[1] == column_name for row in rows)


def _migrate_legacy_users(conn: sqlite3.Connection) -> None:
    if not _column_exists(conn, "users", "is_subscribed"):
        conn.execute("ALTER TABLE users ADD COLUMN is_subscribed INTEGER NOT NULL DEFAULT 1")
    if not _column_exists(conn, "users", "is_blocked"):
        conn.execute("ALTER TABLE users ADD COLUMN is_blocked INTEGER NOT NULL DEFAULT 0")
    if not _column_exists(conn, "users", "full_name"):
        conn.execute("ALTER TABLE users ADD COLUMN full_name TEXT")
    if not _column_exists(conn, "users", "created_at"):
        conn.execute("ALTER TABLE users ADD COLUMN created_at TEXT DEFAULT ''")
    if not _column_exists(conn, "users", "updated_at"):
        conn.execute("ALTER TABLE users ADD COLUMN updated_at TEXT DEFAULT ''")
    if not _column_exists(conn, "users", "last_message_at"):
        conn.execute("ALTER TABLE users ADD COLUMN last_message_at TEXT")