from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from config.settings import BASE_DIR, settings
from database.queries import export_users_txt, get_stats, get_user, set_block_status
from keyboards.admin import admin_menu, cancel_keyboard
from services.broadcast import broadcast_message
from services.messaging import send_admin_reply
from states.admin_states import AdminStates
from utils.helpers import SUPPORTED_CONTENT_TYPES, detect_content_type
from html import escape


logger = logging.getLogger(__name__)
admin_router = Router()

EXPORT_DIR = BASE_DIR / "data" / "exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def format_user_label(user: dict) -> str:
    username = (user.get("username") or "").strip()
    if username and username != "-":
        username = username.lstrip("@")
        return f"@{escape(username)}"

    full_name = (user.get("full_name") or "").strip()
    if full_name and full_name != "-":
        return f"{escape(full_name)} (<code>{user['user_id']}</code>)"

    return f"<code>{user['user_id']}</code>"


@admin_router.message(Command("admin"), F.from_user.id == settings.admin_id)
async def admin_panel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("⚙ <b>Админ-панель</b>", reply_markup=admin_menu())


@admin_router.callback_query(F.from_user.id == settings.admin_id, F.data == "admin:broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(AdminStates.waiting_broadcast_content)
    await callback.message.answer(
        "Отправьте сообщение для рассылки. "
        "Поддерживаются: текст, фото, видео, документ, голосовое, аудио, кружок.\n\n"
        "/cancel — отмена",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@admin_router.message(AdminStates.waiting_broadcast_content, F.from_user.id == settings.admin_id)
async def admin_broadcast_send(message: Message, state: FSMContext, bot: Bot) -> None:
    content_type = detect_content_type(message)
    if content_type not in SUPPORTED_CONTENT_TYPES:
        await message.answer("Неподдерживаемый тип для рассылки.")
        return

    stats = await broadcast_message(bot, message)

    await state.clear()
    await message.answer(
        "✅ Рассылка завершена.\n"
        f"Отправлено: <b>{stats['sent']}</b>\n"
        f"Заблокировали бота: <b>{stats['blocked']}</b>\n"
        f"Ошибок: <b>{stats['failed']}</b>",
        reply_markup=admin_menu(),
    )


@admin_router.callback_query(F.from_user.id == settings.admin_id, F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery) -> None:
    stats = get_stats()
    await callback.message.answer(
        "📊 <b>Статистика</b>\n"
        f"Всего пользователей: <b>{stats['total_users']}</b>\n"
        f"Активных: <b>{stats['active_users']}</b>\n"
        f"Заблокированных: <b>{stats['blocked_users']}</b>\n"
        f"Входящих сообщений: <b>{stats['inbound_messages']}</b>\n"
        f"Исходящих ответов: <b>{stats['outbound_messages']}</b>",
        reply_markup=admin_menu(),
    )
    await callback.answer()


@admin_router.callback_query(F.from_user.id == settings.admin_id, F.data == "admin:export_txt")
async def admin_export_txt(callback: CallbackQuery) -> None:
    path = export_users_txt(EXPORT_DIR / "users_export.txt")
    await callback.message.answer_document(FSInputFile(path), caption="TXT-экспорт пользователей")
    await callback.answer()


@admin_router.callback_query(F.from_user.id == settings.admin_id, F.data.startswith("admin:reply:"))
async def admin_reply_start(callback: CallbackQuery, state: FSMContext) -> None:
    user_id = int(callback.data.split(":")[-1])
    user = get_user(user_id)
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_reply_content)
    await state.update_data(reply_user_id=user_id)
    user_label = format_user_label(user)
    await callback.message.answer(
        f"Отправьте ответ пользователю {user_label}.\n\n/cancel — отмена",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@admin_router.message(AdminStates.waiting_reply_content, F.from_user.id == settings.admin_id)
async def admin_reply_send(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    user_id = int(data.get("reply_user_id", 0))
    if not user_id:
        await state.clear()
        await message.answer("Целевой пользователь не найден.", reply_markup=admin_menu())
        return

    content_type = detect_content_type(message)
    if content_type not in SUPPORTED_CONTENT_TYPES:
        await message.answer("Неподдерживаемый тип ответа.")
        return

    try:
        await send_admin_reply(bot, user_id, message)
        user = get_user(user_id)
        user_label = format_user_label(user) if user else f"<code>{user_id}</code>"
        await message.answer(
            f"✅ Ответ пользователю {user_label} отправлен.",
            reply_markup=admin_menu(),
        )
    except Exception:
        logger.exception("Failed to send admin reply to user_id=%s", user_id)
        user = get_user(user_id)
        user_label = format_user_label(user) if user else f"<code>{user_id}</code>"
        await message.answer(
            f"❌ Не удалось отправить ответ пользователю {user_label}.",
            reply_markup=admin_menu(),
        )
    finally:
        await state.clear()


@admin_router.callback_query(F.from_user.id == settings.admin_id, F.data.startswith("admin:block:"))
async def admin_block_user(callback: CallbackQuery) -> None:
    user_id = int(callback.data.split(":")[-1])
    user = get_user(user_id)
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    set_block_status(user_id, True)
    await callback.message.answer(f"⛔ Пользователь <code>{user_id}</code> заблокирован.")
    await callback.answer("Готово")


@admin_router.callback_query(F.from_user.id == settings.admin_id, F.data.startswith("admin:unblock:"))
async def admin_unblock_user(callback: CallbackQuery) -> None:
    user_id = int(callback.data.split(":")[-1])
    user = get_user(user_id)
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    set_block_status(user_id, False)
    await callback.message.answer(f"✅ Пользователь <code>{user_id}</code> разблокирован.")
    await callback.answer("Готово")