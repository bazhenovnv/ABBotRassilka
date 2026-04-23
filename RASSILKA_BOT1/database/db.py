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

CREATE TABLE IF NOT EXISTS calendar_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT UNIQUE,
    title TEXT NOT NULL,
    description TEXT,
    location TEXT,
    starts_at TEXT NOT NULL,
    ends_at TEXT,
    source_url TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_event_reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    event_id INTEGER NOT NULL,
    remind_3_days INTEGER NOT NULL DEFAULT 0,
    remind_1_day INTEGER NOT NULL DEFAULT 0,
    remind_1_hour INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id, event_id),
    FOREIGN KEY(event_id) REFERENCES calendar_events(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS reminder_send_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    event_id INTEGER NOT NULL,
    reminder_type TEXT NOT NULL,
    scheduled_for TEXT NOT NULL,
    sent_at TEXT NOT NULL,
    UNIQUE(user_id, event_id, reminder_type)
);
"""


def get_connection() -> sqlite3.Connection:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        _migrate_legacy_users(conn)
        _migrate_calendar(conn)
        conn.commit()


def _column_exists(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row[1] == column_name for row in rows)


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


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


def _migrate_calendar(conn: sqlite3.Connection) -> None:
    if _table_exists(conn, "calendar_events"):
        if not _column_exists(conn, "calendar_events", "external_id"):
            conn.execute("ALTER TABLE calendar_events ADD COLUMN external_id TEXT")
        if not _column_exists(conn, "calendar_events", "description"):
            conn.execute("ALTER TABLE calendar_events ADD COLUMN description TEXT")
        if not _column_exists(conn, "calendar_events", "location"):
            conn.execute("ALTER TABLE calendar_events ADD COLUMN location TEXT")
        if not _column_exists(conn, "calendar_events", "ends_at"):
            conn.execute("ALTER TABLE calendar_events ADD COLUMN ends_at TEXT")
        if not _column_exists(conn, "calendar_events", "source_url"):
            conn.execute("ALTER TABLE calendar_events ADD COLUMN source_url TEXT")
        if not _column_exists(conn, "calendar_events", "is_active"):
            conn.execute("ALTER TABLE calendar_events ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
        if not _column_exists(conn, "calendar_events", "created_at"):
            conn.execute("ALTER TABLE calendar_events ADD COLUMN created_at TEXT DEFAULT ''")
        if not _column_exists(conn, "calendar_events", "updated_at"):
            conn.execute("ALTER TABLE calendar_events ADD COLUMN updated_at TEXT DEFAULT ''")
