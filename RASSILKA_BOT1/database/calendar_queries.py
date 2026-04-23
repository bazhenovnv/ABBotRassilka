from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from database.db import get_connection
from database.queries import now_iso


REMINDER_FLAGS = {
    "3d": "remind_3_days",
    "1d": "remind_1_day",
    "1h": "remind_1_hour",
}


def parse_iso(dt_value: str | None) -> datetime | None:
    if not dt_value:
        return None
    normalized = dt_value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def upsert_calendar_event(
    *,
    title: str,
    starts_at: str,
    external_id: str | None = None,
    description: str | None = None,
    location: str | None = None,
    ends_at: str | None = None,
    source_url: str | None = None,
    is_active: bool = True,
) -> int:
    current = now_iso()
    with get_connection() as conn:
        if external_id:
            existing = conn.execute(
                "SELECT id FROM calendar_events WHERE external_id=?",
                (external_id,),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE calendar_events
                    SET title=?, description=?, location=?, starts_at=?, ends_at=?, source_url=?, is_active=?, updated_at=?
                    WHERE external_id=?
                    """,
                    (
                        title,
                        description,
                        location,
                        starts_at,
                        ends_at,
                        source_url,
                        1 if is_active else 0,
                        current,
                        external_id,
                    ),
                )
                conn.commit()
                return int(existing[0])

        row = conn.execute(
            """
            INSERT INTO calendar_events (
                external_id, title, description, location, starts_at, ends_at, source_url, is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                external_id,
                title,
                description,
                location,
                starts_at,
                ends_at,
                source_url,
                1 if is_active else 0,
                current,
                current,
            ),
        )
        conn.commit()
        return int(row.lastrowid)


def get_upcoming_events(limit: int = 10) -> list[dict[str, Any]]:
    now = now_iso()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM calendar_events
            WHERE is_active=1 AND starts_at >= ?
            ORDER BY starts_at ASC, id ASC
            LIMIT ?
            """,
            (now, limit),
        ).fetchall()
        return [dict(row) for row in rows]


def get_event_by_id(event_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM calendar_events WHERE id=? AND is_active=1",
            (event_id,),
        ).fetchone()
        return dict(row) if row else None


def get_event_by_external_id(external_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM calendar_events WHERE external_id=? AND is_active=1",
            (external_id,),
        ).fetchone()
        return dict(row) if row else None


def get_user_reminder(event_id: int, user_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM user_event_reminders WHERE event_id=? AND user_id=?",
            (event_id, user_id),
        ).fetchone()
        return dict(row) if row else None


def upsert_user_reminder_flags(
    user_id: int,
    event_id: int,
    *,
    remind_3_days: bool,
    remind_1_day: bool,
    remind_1_hour: bool,
) -> None:
    current = now_iso()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO user_event_reminders (
                user_id, event_id, remind_3_days, remind_1_day, remind_1_hour, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, event_id) DO UPDATE SET
                remind_3_days=excluded.remind_3_days,
                remind_1_day=excluded.remind_1_day,
                remind_1_hour=excluded.remind_1_hour,
                updated_at=excluded.updated_at
            """,
            (
                user_id,
                event_id,
                1 if remind_3_days else 0,
                1 if remind_1_day else 0,
                1 if remind_1_hour else 0,
                current,
                current,
            ),
        )
        conn.commit()


def set_single_reminder_flag(user_id: int, event_id: int, reminder_type: str, enabled: bool) -> None:
    current = get_user_reminder(event_id, user_id)
    remind_3_days = bool(current["remind_3_days"]) if current else False
    remind_1_day = bool(current["remind_1_day"]) if current else False
    remind_1_hour = bool(current["remind_1_hour"]) if current else False

    if reminder_type == "3d":
        remind_3_days = enabled
    elif reminder_type == "1d":
        remind_1_day = enabled
    elif reminder_type == "1h":
        remind_1_hour = enabled
    elif reminder_type == "off":
        remind_3_days = False
        remind_1_day = False
        remind_1_hour = False
    else:
        raise ValueError(f"Unsupported reminder_type: {reminder_type}")

    upsert_user_reminder_flags(
        user_id,
        event_id,
        remind_3_days=remind_3_days,
        remind_1_day=remind_1_day,
        remind_1_hour=remind_1_hour,
    )


def get_user_active_reminders(user_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT r.*, e.title, e.description, e.location, e.starts_at, e.ends_at, e.source_url
            FROM user_event_reminders r
            JOIN calendar_events e ON e.id = r.event_id
            WHERE r.user_id=?
              AND e.is_active=1
              AND e.starts_at >= ?
              AND (r.remind_3_days=1 OR r.remind_1_day=1 OR r.remind_1_hour=1)
            ORDER BY e.starts_at ASC, e.id ASC
            """,
            (user_id, now_iso()),
        ).fetchall()
        return [dict(row) for row in rows]


def was_reminder_sent(user_id: int, event_id: int, reminder_type: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT 1
            FROM reminder_send_log
            WHERE user_id=? AND event_id=? AND reminder_type=?
            LIMIT 1
            """,
            (user_id, event_id, reminder_type),
        ).fetchone()
        return row is not None


def mark_reminder_sent(user_id: int, event_id: int, reminder_type: str, scheduled_for: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO reminder_send_log (user_id, event_id, reminder_type, scheduled_for, sent_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, event_id, reminder_type, scheduled_for, now_iso()),
        )
        conn.commit()


def get_due_reminders(now: datetime | None = None) -> list[dict[str, Any]]:
    now_dt = now or datetime.now(timezone.utc)
    rows_out: list[dict[str, Any]] = []

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT r.user_id, r.event_id, r.remind_3_days, r.remind_1_day, r.remind_1_hour,
                   e.title, e.description, e.location, e.starts_at, e.ends_at, e.source_url
            FROM user_event_reminders r
            JOIN calendar_events e ON e.id = r.event_id
            JOIN users u ON u.user_id = r.user_id
            WHERE e.is_active=1
              AND u.is_subscribed=1
              AND u.is_blocked=0
              AND e.starts_at >= ?
              AND (r.remind_3_days=1 OR r.remind_1_day=1 OR r.remind_1_hour=1)
            ORDER BY e.starts_at ASC
            """,
            (now_iso(),),
        ).fetchall()

    windows = {
        "3d": 3 * 24 * 3600,
        "1d": 24 * 3600,
        "1h": 3600,
    }

    for row in rows:
        item = dict(row)
        event_dt = parse_iso(item["starts_at"])
        if not event_dt:
            continue
        seconds_left = (event_dt - now_dt).total_seconds()
        for reminder_type, seconds_before in windows.items():
            flag_name = REMINDER_FLAGS[reminder_type]
            if not item.get(flag_name):
                continue
            if was_reminder_sent(item["user_id"], item["event_id"], reminder_type):
                continue
            lower_bound = seconds_before - 60
            upper_bound = seconds_before
            if lower_bound <= seconds_left <= upper_bound:
                reminder = dict(item)
                reminder["reminder_type"] = reminder_type
                reminder["scheduled_for"] = (event_dt - timedelta(seconds=seconds_before)).isoformat()
                rows_out.append(reminder)
    return rows_out


from datetime import timedelta  # noqa: E402
