from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config.settings import settings
from database.queries import get_user, upsert_user
from keyboards.user import subscribe_menu, unsubscribe_menu
from services.calendar_sync import calendar_sync_service
from services.cooldown import get_remaining_seconds, start_cooldown
from services.messaging import relay_user_message_to_admin
from services.subscription import subscribe_user, unsubscribe_user
from utils.calendar_format import format_event_card
from utils.helpers import SUPPORTED_CONTENT_TYPES, detect_content_type
from database.calendar_queries import get_event_by_external_id
from keyboards.calendar import event_card_keyboard


logger = logging.getLogger(__name__)
user_router = Router()


PRIVACY_POLICY_TEXT = (
    "<b>Политика конфиденциальности</b>\n\n"
    "Используя бот <b>«АБ Партнер»</b>, вы соглашаетесь с обработкой данных, "
    "необходимых для работы сервиса.\n\n"
    "<b>Какие данные обрабатываются:</b>\n"
    "• Telegram ID;\n"
    "• username, имя и отображаемое имя в Telegram;\n"
    "• отправленные вами сообщения, вопросы и вложения (текст, фото, видео, документы, аудио и другие поддерживаемые файлы);\n"
    "• технические данные, необходимые для доставки сообщений и работы функций бота.\n\n"
    "<b>Для чего используются данные:</b>\n"
    "• для приёма и обработки ваших обращений;\n"
    "• для передачи вопроса администратору и отправки ответа;\n"
    "• для управления подпиской, ограничениями на отправку сообщений и безопасностью работы бота;\n"
    "• для хранения персональных настроек напоминаний по событиям проекта «АБ| Афиша».\n\n"
    "<b>Передача данных:</b>\n"
    "Ваши сообщения и вложения передаются администратору бота только в рамках обработки обращения. "
    "Данные не предназначены для публичного распространения через бот.\n\n"
    "<b>Хранение и удаление:</b>\n"
    "Данные могут храниться в базе бота в объёме, необходимом для работы сервиса и истории обращений. "
    "Для прекращения использования бота вы можете нажать <b>«Отписаться»</b>.\n\n"
    "<b>Важно:</b>\n"
    "Не отправляйте через бот банковские данные, пароли, коды подтверждения и иную чувствительную информацию, "
    "если это не требуется и не согласовано отдельно.\n\n"
    "Продолжение использования бота означает согласие с настоящей политикой конфиденциальности."
)


def cooldown_text(seconds: int) -> str:
    return (
        "Сообщение отправлено, ожидайте ответа!\n"
        f"Следующий вопрос сможете задать через <b>{seconds} сек.</b>"
    )


async def update_cooldown_message(bot: Bot, chat_id: int, message_id: int, start_seconds: int) -> None:
    remaining = start_seconds

    while remaining > 10:
        await asyncio.sleep(5)
        remaining -= 5
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=cooldown_text(remaining),
            )
        except TelegramBadRequest:
            break
        except Exception:
            logger.exception(
                "Cooldown message update failed on 5-sec step: chat_id=%s message_id=%s",
                chat_id,
                message_id,
            )
            break

    while remaining > 0:
        await asyncio.sleep(1)
        remaining -= 1
        try:
            if remaining > 0:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=cooldown_text(remaining),
                )
            else:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text="✅ Ограничение снято. Теперь можете задать следующий вопрос.",
                )
        except TelegramBadRequest:
            break
        except Exception:
            logger.exception(
                "Cooldown message update failed on 1-sec step: chat_id=%s message_id=%s",
                chat_id,
                message_id,
            )
            break


def _extract_afisha_event_id(command: CommandObject | None) -> str | None:
    if not command or not command.args:
        return None
    payload = command.args.strip()
    if not payload.startswith("afisha_"):
        return None
    event_id = payload.removeprefix("afisha_").strip()
    return event_id or None


async def _show_afisha_event_from_deeplink(message: Message, event_id: str) -> bool:
    external_id = f"calendar_event:{event_id}"
    event = get_event_by_external_id(external_id)

    if not event:
        try:
            event = await asyncio.to_thread(calendar_sync_service.sync_event_by_public_id, event_id)
        except Exception:
            logger.exception("Failed to sync event for deep-link: event_id=%s", event_id)
            await message.answer(
                "Не удалось загрузить событие из «АБ| Афиша». Попробуйте открыть его позже или перейдите в раздел календаря вручную.",
                reply_markup=unsubscribe_menu(),
            )
            return False

    await message.answer(
        "📅 <b>Открываю событие из «АБ| Афиша»</b>",
        reply_markup=unsubscribe_menu(),
    )
    await message.answer(
        format_event_card(event),
        reply_markup=event_card_keyboard(int(event["id"]), 0),
    )
    return True


@user_router.message(CommandStart())
async def start_handler(message: Message, command: CommandObject | None = None) -> None:
    if message.from_user.id == settings.admin_id:
        from keyboards.admin import admin_menu
        await message.answer("⚙ <b>Админ-панель</b>", reply_markup=admin_menu())
        return

    upsert_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.full_name,
    )
    user = get_user(message.from_user.id)

    if not user or not user.get("is_subscribed"):
        await message.answer(
            "Добро пожаловать. Нажмите <b>Подписаться</b>, чтобы продолжить.",
            reply_markup=subscribe_menu(),
        )
        return

    afisha_event_id = _extract_afisha_event_id(command)
    if afisha_event_id:
        await _show_afisha_event_from_deeplink(message, afisha_event_id)
        return

    remaining = get_remaining_seconds(message.from_user.id)
    if remaining > 0:
        await message.answer(
            f"Добро пожаловать. Сейчас действует ограничение на отправку нового вопроса: "
            f"<b>{remaining} сек.</b>",
            reply_markup=unsubscribe_menu(),
        )
        return

    await message.answer(
        "🤖 <b>Добро пожаловать в Ваш персональный помощник!</b>\n\n"
        "Вы можете задать вопрос в <b>«АБ Партнер»</b> "
        "по полученной информации от <b>«АБ | ВАЖНО»</b>.\n\n"
        "Также доступен раздел <b>«АБ| Афиша»</b> с ближайшими событиями и напоминаниями.\n\n"
        "✍️ Пишите вопрос сразу в строку сообщения или откройте раздел с афишей ниже.",
        reply_markup=unsubscribe_menu(),
    )


@user_router.message(Command("privacy"))
async def privacy_command(message: Message) -> None:
    await message.answer(PRIVACY_POLICY_TEXT)


@user_router.callback_query(F.data == "user:privacy")
async def privacy_callback(callback: CallbackQuery) -> None:
    await callback.message.answer(PRIVACY_POLICY_TEXT)
    await callback.answer()


@user_router.callback_query(F.data == "user:subscribe")
async def subscribe(callback: CallbackQuery) -> None:
    subscribe_user(
        callback.from_user.id,
        callback.from_user.username,
        callback.from_user.first_name,
        callback.from_user.full_name,
    )
    await callback.message.edit_text("✅ Вы успешно подписались!")
    await callback.message.answer(
        "Теперь можно писать вопрос прямо в нижнюю строку ввода и пользоваться разделом «АБ| Афиша».",
        reply_markup=unsubscribe_menu(),
    )
    await callback.answer()


@user_router.callback_query(F.data == "user:unsubscribe")
async def unsubscribe(callback: CallbackQuery, state: FSMContext) -> None:
    unsubscribe_user(callback.from_user.id)
    await state.clear()
    await callback.message.edit_text("❌ Вы отписались.")
    await callback.message.answer(
        "Чтобы продолжить, подпишитесь снова.",
        reply_markup=subscribe_menu(),
    )
    await callback.answer()


@user_router.callback_query(F.data == "user:ask_question")
async def ask_question(callback: CallbackQuery) -> None:
    remaining = get_remaining_seconds(callback.from_user.id)
    if remaining > 0:
        await callback.answer("Дождитесь окончания запрета на отправку", show_alert=True)
        return

    await callback.answer("Напишите вопрос в нижнюю строку сообщения.", show_alert=True)


@user_router.message(F.chat.type == "private", F.from_user.id != settings.admin_id)
async def handle_user_message(message: Message, bot: Bot) -> None:
    user = get_user(message.from_user.id)
    if not user or not user.get("is_subscribed"):
        await message.answer("Сначала подпишитесь.", reply_markup=subscribe_menu())
        return

    if user.get("is_blocked"):
        await message.answer("Отправка сообщений недоступна.")
        return

    content_type = detect_content_type(message)
    if content_type not in SUPPORTED_CONTENT_TYPES:
        await message.answer(
            "Этот тип сообщения не поддерживается. "
            "Отправьте текст, фото, видео, документ, голосовое, аудио или кружок."
        )
        return

    remaining = get_remaining_seconds(message.from_user.id)
    if remaining > 0:
        await message.answer("Дождитесь окончания запрета на отправку")
        return

    await relay_user_message_to_admin(bot, message)
    start_cooldown(message.from_user.id)

    sent = await message.answer(cooldown_text(settings.cooldown_seconds))
    asyncio.create_task(
        update_cooldown_message(
            bot=bot,
            chat_id=message.chat.id,
            message_id=sent.message_id,
            start_seconds=settings.cooldown_seconds,
        )
    )
