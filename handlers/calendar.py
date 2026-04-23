from __future__ import annotations

import asyncio
import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from config.settings import settings
from database.calendar_queries import (
    get_event_by_id,
    get_upcoming_events,
    get_user_active_reminders,
    get_user_reminder,
    set_single_reminder_flag,
)
from keyboards.calendar import (
    event_card_keyboard,
    events_list_keyboard,
    my_reminders_keyboard,
    reminder_settings_keyboard,
)
from database.queries import get_user
from keyboards.user import subscribe_menu, unsubscribe_menu
from services.calendar_sync import calendar_sync_service
from utils.calendar_format import format_event_card, format_event_datetime, reminder_status_text


logger = logging.getLogger(__name__)
calendar_router = Router()
PAGE_SIZE = 5


def _user_has_access(user_id: int) -> bool:
    user = get_user(user_id)
    return bool(user and user.get("is_subscribed") and not user.get("is_blocked"))


async def _ensure_access(callback: CallbackQuery) -> bool:
    if _user_has_access(callback.from_user.id):
        return True
    await callback.message.answer(
        "Сначала подпишитесь, чтобы открыть раздел «АБ| Афиша».",
        reply_markup=subscribe_menu(),
    )
    await callback.answer()
    return False


async def _sync_upcoming_events_safely(limit: int = 30) -> None:
    try:
        synced = await asyncio.to_thread(calendar_sync_service.sync_upcoming_events, limit)
        logger.info("Calendar sync completed: synced=%s", synced)
    except Exception:
        logger.exception("Calendar sync failed; using cached SQLite events")


async def send_event_card_message(message: Message, event: dict, page: int = 0) -> None:
    await message.answer(
        format_event_card(event),
        reply_markup=event_card_keyboard(int(event["id"]), int(page)),
    )


@calendar_router.message(F.text == "/calendar")
async def calendar_command(message: Message) -> None:
    if message.from_user.id == settings.admin_id:
        return
    if not _user_has_access(message.from_user.id):
        await message.answer("Сначала подпишитесь, чтобы открыть раздел «АБ| Афиша».", reply_markup=subscribe_menu())
        return

    await _sync_upcoming_events_safely(limit=30)
    events = get_upcoming_events(limit=30)
    if not events:
        await message.answer("Пока нет ближайших событий «АБ| Афиша».", reply_markup=unsubscribe_menu())
        return
    await message.answer("📅 <b>Ближайшие события «АБ| Афиша»</b>", reply_markup=events_list_keyboard(events, 0, PAGE_SIZE))


@calendar_router.callback_query(F.data == "calendar:menu")
async def calendar_menu(callback: CallbackQuery) -> None:
    if not await _ensure_access(callback):
        return
    await callback.message.answer("Открыт раздел «АБ| Афиша».", reply_markup=unsubscribe_menu())
    await callback.answer()


@calendar_router.callback_query(F.data.startswith("calendar:list:"))
async def calendar_list(callback: CallbackQuery) -> None:
    if not await _ensure_access(callback):
        return

    await _sync_upcoming_events_safely(limit=30)
    events = get_upcoming_events(limit=30)
    if not events:
        await callback.message.answer("Пока нет ближайших событий «АБ| Афиша».", reply_markup=unsubscribe_menu())
        await callback.answer()
        return

    page = int(callback.data.split(":")[-1])
    await callback.message.answer(
        "📅 <b>Ближайшие события «АБ| Афиша»</b>",
        reply_markup=events_list_keyboard(events, page, PAGE_SIZE),
    )
    await callback.answer()


@calendar_router.callback_query(F.data.startswith("calendar:event:"))
async def calendar_event(callback: CallbackQuery) -> None:
    if not await _ensure_access(callback):
        return
    _, _, event_id, page = callback.data.split(":")
    event = get_event_by_id(int(event_id))
    if not event:
        await callback.answer("Событие не найдено или уже недоступно.", show_alert=True)
        return
    await callback.message.answer(
        format_event_card(event),
        reply_markup=event_card_keyboard(int(event_id), int(page)),
    )
    await callback.answer()


@calendar_router.callback_query(F.data.startswith("calendar:reminders:"))
async def calendar_reminders(callback: CallbackQuery) -> None:
    if not await _ensure_access(callback):
        return
    _, _, event_id, page = callback.data.split(":")
    event = get_event_by_id(int(event_id))
    if not event:
        await callback.answer("Событие не найдено.", show_alert=True)
        return
    reminder = get_user_reminder(int(event_id), callback.from_user.id)
    await callback.message.answer(
        f"🔔 <b>Напоминания для события</b>\n\n{event['title']}\n{reminder_status_text(reminder)}",
        reply_markup=reminder_settings_keyboard(int(event_id), int(page), reminder),
    )
    await callback.answer()


@calendar_router.callback_query(F.data.startswith("calendar:toggle:"))
async def calendar_toggle(callback: CallbackQuery) -> None:
    if not await _ensure_access(callback):
        return
    _, _, event_id, reminder_type, page = callback.data.split(":")
    current = get_user_reminder(int(event_id), callback.from_user.id)

    if reminder_type == "off":
        enabled = False
    else:
        flag_map = {"3d": "remind_3_days", "1d": "remind_1_day", "1h": "remind_1_hour"}
        enabled = not bool(current and current.get(flag_map[reminder_type]))

    set_single_reminder_flag(callback.from_user.id, int(event_id), reminder_type, enabled)
    reminder = get_user_reminder(int(event_id), callback.from_user.id)
    event = get_event_by_id(int(event_id))
    await callback.message.answer(
        f"🔔 <b>Настройки обновлены</b>\n\n{event['title'] if event else 'Событие'}\n{reminder_status_text(reminder)}",
        reply_markup=reminder_settings_keyboard(int(event_id), int(page), reminder),
    )
    await callback.answer("Настройки сохранены")


@calendar_router.callback_query(F.data == "calendar:my")
async def calendar_my(callback: CallbackQuery) -> None:
    if not await _ensure_access(callback):
        return
    items = get_user_active_reminders(callback.from_user.id)
    if not items:
        await callback.message.answer(
            "У вас пока нет активных напоминаний по событиям.",
            reply_markup=unsubscribe_menu(),
        )
        await callback.answer()
        return

    lines = ["🔔 <b>Мои напоминания</b>"]
    for item in items[:15]:
        flags = []
        if item.get("remind_3_days"):
            flags.append("3 дня")
        if item.get("remind_1_day"):
            flags.append("1 день")
        if item.get("remind_1_hour"):
            flags.append("1 час")
        lines.append(
            f"\n• <b>{item['title']}</b>\n"
            f"  {format_event_datetime(item.get('starts_at'), item.get('ends_at'))}\n"
            f"  Напомнить: {', '.join(flags)}"
        )

    await callback.message.answer("\n".join(lines), reply_markup=my_reminders_keyboard(items))
    await callback.answer()
