from __future__ import annotations

from config.settings import settings
from database.calendar_queries import parse_iso


REMINDER_LABELS = {
    "3d": "за 3 дня",
    "1d": "за 1 день",
    "1h": "за 1 час",
}


def format_event_datetime(starts_at: str | None, ends_at: str | None = None) -> str:
    start_dt = parse_iso(starts_at)
    end_dt = parse_iso(ends_at)
    if not start_dt:
        return "Дата не указана"

    local_start = start_dt.astimezone(settings.calendar_timezone)
    text = local_start.strftime("%d.%m.%Y %H:%M")
    if end_dt:
        local_end = end_dt.astimezone(settings.calendar_timezone)
        text += f" — {local_end.strftime('%d.%m.%Y %H:%M')}"
    return text


def format_event_card(event: dict) -> str:
    parts = [
        f"<b>{event['title']}</b>",
        f"🗓 <b>Когда:</b> {format_event_datetime(event.get('starts_at'), event.get('ends_at'))}",
    ]
    if event.get("location"):
        parts.append(f"📍 <b>Где:</b> {event['location']}")
    if event.get("description"):
        parts.append(f"\n{event['description']}")
    if event.get("source_url"):
        parts.append(f"\n🔗 <b>Источник:</b> {event['source_url']}")
    return "\n".join(parts)


def reminder_status_text(reminder: dict | None) -> str:
    if not reminder:
        return "Напоминания пока отключены."
    enabled = []
    if reminder.get("remind_3_days"):
        enabled.append("за 3 дня")
    if reminder.get("remind_1_day"):
        enabled.append("за 1 день")
    if reminder.get("remind_1_hour"):
        enabled.append("за 1 час")
    if not enabled:
        return "Напоминания пока отключены."
    return "Активно: " + ", ".join(enabled)
