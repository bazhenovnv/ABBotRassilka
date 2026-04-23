from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError

from config.settings import settings
from database.calendar_queries import parse_iso
from database.calendar_queries import get_due_reminders, mark_reminder_sent
from database.queries import set_block_status
from keyboards.user import unsubscribe_menu


logger = logging.getLogger(__name__)

REMINDER_LABELS = {
    "3d": "за 3 дня",
    "1d": "за 1 день",
    "1h": "за 1 час",
}


def build_reminder_text(item: dict) -> str:
    when_label = REMINDER_LABELS.get(item["reminder_type"], "заранее")
    event_dt = parse_iso(item.get("starts_at"))
    starts_at = item.get("starts_at")
    if event_dt:
        starts_at = event_dt.astimezone(settings.calendar_timezone).strftime("%d.%m.%Y %H:%M")
    location = f"\n📍 <b>Где:</b> {item['location']}" if item.get("location") else ""
    description = f"\n\n{item['description']}" if item.get("description") else ""
    source = f"\n\n🔗 <b>Источник:</b> {item['source_url']}" if item.get("source_url") else ""
    return (
        f"🔔 <b>Напоминание {when_label}</b>\n\n"
        f"<b>{item['title']}</b>\n"
        f"🗓 <b>Начало:</b> {starts_at}"
        f"{location}"
        f"{description}"
        f"{source}"
    )


async def send_due_reminders(bot: Bot) -> None:
    due_items = get_due_reminders()
    if not due_items:
        return

    for item in due_items:
        try:
            await bot.send_message(
                item["user_id"],
                build_reminder_text(item),
                reply_markup=unsubscribe_menu(),
            )
            mark_reminder_sent(
                item["user_id"],
                item["event_id"],
                item["reminder_type"],
                item["scheduled_for"],
            )
        except TelegramForbiddenError:
            set_block_status(item["user_id"], True)
            logger.warning("User blocked bot during reminder delivery: user_id=%s", item["user_id"])
        except Exception:
            logger.exception(
                "Failed to send reminder: user_id=%s event_id=%s type=%s",
                item["user_id"],
                item["event_id"],
                item["reminder_type"],
            )


async def reminder_worker(bot: Bot) -> None:
    while True:
        try:
            await send_due_reminders(bot)
        except Exception:
            logger.exception("Reminder worker iteration failed")
        await asyncio.sleep(settings.reminder_check_interval_seconds)
