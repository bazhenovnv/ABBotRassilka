from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def admin_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📢 Рассылка", callback_data="admin:broadcast")
    kb.button(text="📊 Статистика", callback_data="admin:stats")
    kb.button(text="📄 Экспорт TXT", callback_data="admin:export_txt")
    kb.adjust(1, 1, 1)
    return kb.as_markup()


def reply_button(user_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⛔ Блок", callback_data=f"admin:block:{user_id}")
    kb.button(text="✅ Разблок", callback_data=f"admin:unblock:{user_id}")
    kb.button(text="💬 Ответить", callback_data=f"admin:reply:{user_id}")
    kb.adjust(2, 1)
    return kb.as_markup()


def reply_again_button(user_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⛔ Блок", callback_data=f"admin:block:{user_id}")
    kb.button(text="✅ Разблок", callback_data=f"admin:unblock:{user_id}")
    kb.button(text="🔄 Ответить снова", callback_data=f"admin:reply:{user_id}")
    kb.adjust(2, 1)
    return kb.as_markup()


def cancel_keyboard(prefix: str = "common:cancel") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="↩ Отмена", callback_data=prefix)
    return kb.as_markup()
