from __future__ import annotations

import logging
from html import escape

from aiogram import Bot
from aiogram.types import Message

from config.settings import settings
from database.queries import get_last_incoming_message_preview, log_message, update_last_message_at
from keyboards.admin import reply_button
from keyboards.user import broadcast_menu
from utils.helpers import detect_content_type, extract_text_preview


logger = logging.getLogger(__name__)

admin_messages: dict[int, dict] = {}
pending_users: set[int] = set()


def build_user_reply_header(question_text: str | None) -> str:
    if not question_text:
        return "🟢 <b>Ответ от АБ Партнер:</b>"

    normalized = " ".join(question_text.split())
    if len(normalized) > 220:
        normalized = normalized[:217].rstrip() + "..."

    return (
        f"🟨 <b>Ваш вопрос:</b>\n<i>«{escape(normalized)}»</i>\n\n"
        "🟢 <b>Ответ от АБ Партнер:</b>"
    )


def build_admin_new_header(user_id: int, full_name: str, username: str, content_type: str) -> str:
    pending_count = len(pending_users)
    return (
        f"🟡 <b>Новое сообщение ({pending_count})</b>\n\n"
        f"<b>Пользователь:</b> {full_name}\n"
        f"<b>ID:</b> <code>{user_id}</code>\n"
        f"<b>Username:</b> {username}\n"
        f"<b>Тип:</b> {content_type}"
    )


def build_admin_answered_header(user_id: int, full_name: str, username: str, content_type: str) -> str:
    pending_count = len(pending_users)
    return (
        "🟢 <b>Дан ответ</b>\n\n"
        f"<b>Пользователь:</b> {full_name}\n"
        f"<b>ID:</b> <code>{user_id}</code>\n"
        f"<b>Username:</b> {username}\n"
        f"<b>Тип:</b> {content_type}\n\n"
        f"<b>Ожидают ответа:</b> {pending_count}"
    )


def build_admin_media_caption(
    user_id: int,
    full_name: str,
    username: str,
    content_type: str,
    user_caption: str | None,
) -> str:
    base = (
        "🟡 <b>Новое сообщение</b>\n\n"
        f"<b>Пользователь:</b> {full_name}\n"
        f"<b>ID:</b> <code>{user_id}</code>\n"
        f"<b>Username:</b> {username}\n"
        f"<b>Тип:</b> {content_type}"
    )

    if user_caption:
        return f"{base}\n\n<b>Текст:</b>\n{user_caption}"

    return base


async def relay_user_message_to_admin(bot: Bot, message: Message) -> None:
    user = message.from_user
    user_id = user.id
    username = f"@{user.username}" if user.username else "-"
    full_name = user.full_name
    content_type = detect_content_type(message)
    preview = extract_text_preview(message)

    pending_users.add(user_id)

    if message.text:
        admin_text = (
            f"{build_admin_new_header(user_id, full_name, username, content_type)}\n\n"
            f"<b>Сообщение:</b>\n{message.text}"
        )

        sent = await bot.send_message(
            settings.admin_id,
            admin_text,
            reply_markup=reply_button(user_id),
        )

    elif message.photo:
        caption = build_admin_media_caption(
            user_id=user_id,
            full_name=full_name,
            username=username,
            content_type=content_type,
            user_caption=message.caption,
        )

        sent = await bot.send_photo(
            chat_id=settings.admin_id,
            photo=message.photo[-1].file_id,
            caption=caption,
            reply_markup=reply_button(user_id),
        )

    elif message.video:
        caption = build_admin_media_caption(
            user_id=user_id,
            full_name=full_name,
            username=username,
            content_type=content_type,
            user_caption=message.caption,
        )

        sent = await bot.send_video(
            chat_id=settings.admin_id,
            video=message.video.file_id,
            caption=caption,
            reply_markup=reply_button(user_id),
        )

    else:
        sent = await bot.send_message(
            settings.admin_id,
            build_admin_new_header(user_id, full_name, username, content_type),
            reply_markup=reply_button(user_id),
        )

        await bot.copy_message(
            chat_id=settings.admin_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )

    admin_messages[user_id] = {
        "message_id": sent.message_id,
        "full_name": full_name,
        "username": username,
        "content_type": content_type,
        "is_media": bool(message.photo or message.video),
    }

    log_message(user_id, "incoming", content_type, preview, sent.message_id)
    update_last_message_at(user_id)

    logger.info("Relayed user message to admin: user_id=%s type=%s", user_id, content_type)


async def send_admin_reply(bot: Bot, user_id: int, admin_message: Message) -> None:
    content_type = detect_content_type(admin_message)
    preview = extract_text_preview(admin_message)
    question_preview = get_last_incoming_message_preview(user_id)
    reply_header = build_user_reply_header(question_preview)

    if admin_message.text:
        text = f"{reply_header}\n{admin_message.html_text}"
        sent = await bot.send_message(user_id, text)
    else:
        await bot.send_message(user_id, reply_header)
        sent = await bot.copy_message(
            chat_id=user_id,
            from_chat_id=admin_message.chat.id,
            message_id=admin_message.message_id,
        )

    log_message(user_id, "outgoing", content_type, preview, sent.message_id)
    logger.info("Sent admin reply: user_id=%s type=%s", user_id, content_type)

    if user_id in pending_users:
        pending_users.discard(user_id)

    if user_id in admin_messages:
        try:
            info = admin_messages[user_id]

            if not info["is_media"]:
                await bot.edit_message_text(
                    chat_id=settings.admin_id,
                    message_id=info["message_id"],
                    text=build_admin_answered_header(
                        user_id,
                        info["full_name"],
                        info["username"],
                        info["content_type"],
                    ),
                    reply_markup=reply_button(user_id),
                )
            else:
                await bot.edit_message_caption(
                    chat_id=settings.admin_id,
                    message_id=info["message_id"],
                    caption=build_admin_answered_header(
                        user_id,
                        info["full_name"],
                        info["username"],
                        info["content_type"],
                    ),
                    reply_markup=reply_button(user_id),
                )

        except Exception:
            logger.exception("Failed to update admin message status for user_id=%s", user_id)


async def send_broadcast_copy(bot: Bot, user_id: int, admin_message: Message) -> None:
    await bot.copy_message(
        chat_id=user_id,
        from_chat_id=admin_message.chat.id,
        message_id=admin_message.message_id,
        reply_markup=broadcast_menu(),
    )
