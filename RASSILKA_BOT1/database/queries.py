from __future__ import annotations

from datetime import datetime, timezone
import csv
from pathlib import Path
from typing import Any

from database.db import get_connection


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert_user(user_id: int, username: str | None, first_name: str | None, full_name: str | None) -> None:
    current = now_iso()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO users (user_id, username, first_name, full_name, is_subscribed, is_blocked, created_at, updated_at)
            VALUES (?, ?, ?, ?, 1, 0, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name,
                full_name=excluded.full_name,
                is_subscribed=1,
                updated_at=excluded.updated_at
            """,
            (user_id, username or "-", first_name or "-", full_name or "-", current, current),
        )
        conn.commit()


def set_subscription(user_id: int, is_subscribed: bool) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET is_subscribed=?, updated_at=? WHERE user_id=?",
            (1 if is_subscribed else 0, now_iso(), user_id),
        )
        conn.commit()


def set_block_status(user_id: int, is_blocked: bool) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET is_blocked=?, updated_at=? WHERE user_id=?",
            (1 if is_blocked else 0, now_iso(), user_id),
        )
        conn.commit()


def get_user(user_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        return dict(row) if row else None


def get_all_users(active_only: bool = False) -> list[dict[str, Any]]:
    query = "SELECT * FROM users"
    if active_only:
        query += " WHERE is_subscribed=1 AND is_blocked=0"
    query += " ORDER BY created_at DESC, user_id DESC"
    with get_connection() as conn:
        rows = conn.execute(query).fetchall()
        return [dict(row) for row in rows]


def update_last_message_at(user_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET last_message_at=?, updated_at=? WHERE user_id=?",
            (now_iso(), now_iso(), user_id),
        )
        conn.commit()


def set_cooldown(user_id: int, until_ts: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO cooldowns (user_id, until_ts) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET until_ts=excluded.until_ts",
            (user_id, until_ts),
        )
        conn.commit()


def get_cooldown_until(user_id: int) -> int | None:
    with get_connection() as conn:
        row = conn.execute("SELECT until_ts FROM cooldowns WHERE user_id=?", (user_id,)).fetchone()
        return int(row[0]) if row else None


def clear_cooldown(user_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM cooldowns WHERE user_id=?", (user_id,))
        conn.commit()


def cleanup_expired_cooldowns(now_ts: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM cooldowns WHERE until_ts <= ?", (now_ts,))
        conn.commit()


def log_message(
    user_id: int,
    direction: str,
    content_type: str,
    text: str | None,
    telegram_message_id: int | None,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO message_log (user_id, direction, content_type, text, telegram_message_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, direction, content_type, text, telegram_message_id, now_iso()),
        )
        conn.commit()


def get_stats() -> dict[str, int]:
    with get_connection() as conn:
        total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        active_users = conn.execute(
            "SELECT COUNT(*) FROM users WHERE is_subscribed=1 AND is_blocked=0"
        ).fetchone()[0]
        blocked_users = conn.execute(
            "SELECT COUNT(*) FROM users WHERE is_blocked=1"
        ).fetchone()[0]
        inbound_messages = conn.execute(
            "SELECT COUNT(*) FROM message_log WHERE direction='incoming'"
        ).fetchone()[0]
        outbound_messages = conn.execute(
            "SELECT COUNT(*) FROM message_log WHERE direction='outgoing'"
        ).fetchone()[0]

        return {
            "total_users": total_users,
            "active_users": active_users,
            "blocked_users": blocked_users,
            "inbound_messages": inbound_messages,
            "outbound_messages": outbound_messages,
        }


def export_users_csv(path: Path) -> Path:
    users = get_all_users(active_only=False)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "user_id",
                "username",
                "first_name",
                "full_name",
                "is_subscribed",
                "is_blocked",
                "created_at",
                "updated_at",
                "last_message_at",
            ],
            delimiter=";",
        )
        writer.writeheader()
        writer.writerows(users)
    return path


def export_users_txt(path: Path) -> Path:
    users = get_all_users(active_only=False)
    with path.open("w", encoding="utf-8") as f:
        for user in users:
            f.write(
                f"ID: {user['user_id']} | username: {user['username']} | имя: {user['full_name']} | "
                f"subscribed: {user['is_subscribed']} | blocked: {user['is_blocked']} | "
                f"created_at: {user['created_at']} | last_message_at: {user['last_message_at']}\n"
            )
    return path

def get_last_incoming_message_preview(user_id: int) -> str | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT text
            FROM message_log
            WHERE user_id=? AND direction='incoming'
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()

        if not row:
            return None

        text = (row[0] or '').strip()
        return text or None
