from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def unsubscribe_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📅 АБ| Афиша", callback_data="calendar:list:0")
    kb.button(text="🔔 Мои напоминания", callback_data="calendar:my")
    kb.button(text="🔐 Политика конфиденциальности", callback_data="user:privacy")
    kb.button(text="❌ Отписаться", callback_data="user:unsubscribe")
    kb.adjust(2, 1, 1)
    return kb.as_markup()


def subscribe_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подписаться", callback_data="user:subscribe")
    kb.button(text="🔐 Политика конфиденциальности", callback_data="user:privacy")
    kb.adjust(1)
    return kb.as_markup()


def broadcast_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✍️ Задать вопрос", callback_data="user:ask_question")
    kb.button(text="📅 АБ| Афиша", callback_data="calendar:list:0")
    kb.button(text="🔔 Мои напоминания", callback_data="calendar:my")
    kb.button(text="❌ Отписаться", callback_data="user:unsubscribe")
    kb.adjust(2, 2)
    return kb.as_markup()
