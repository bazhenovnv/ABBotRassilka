from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def events_list_keyboard(events: list[dict], page: int, page_size: int = 5) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    start = page * page_size
    page_events = events[start:start + page_size]

    for event in page_events:
        kb.button(text=event["title"], callback_data=f"calendar:event:{event['id']}:{page}")

    if page > 0:
        kb.button(text="⬅️ Назад", callback_data=f"calendar:list:{page - 1}")
    if start + page_size < len(events):
        kb.button(text="➡️ Далее", callback_data=f"calendar:list:{page + 1}")

    kb.button(text="🔔 Мои напоминания", callback_data="calendar:my")
    kb.button(text="🏠 В меню", callback_data="calendar:menu")
    kb.adjust(1)
    return kb.as_markup()


def event_card_keyboard(event_id: int, page: int = 0) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔔 Настроить напоминания", callback_data=f"calendar:reminders:{event_id}:{page}")
    kb.button(text="📅 К событиям", callback_data=f"calendar:list:{page}")
    kb.button(text="🔔 Мои напоминания", callback_data="calendar:my")
    kb.button(text="🏠 В меню", callback_data="calendar:menu")
    kb.adjust(1)
    return kb.as_markup()


def reminder_settings_keyboard(event_id: int, page: int, reminder: dict | None) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    r3 = "✅" if reminder and reminder.get("remind_3_days") else "▫️"
    r1d = "✅" if reminder and reminder.get("remind_1_day") else "▫️"
    r1h = "✅" if reminder and reminder.get("remind_1_hour") else "▫️"

    kb.button(text=f"{r3} За 3 дня", callback_data=f"calendar:toggle:{event_id}:3d:{page}")
    kb.button(text=f"{r1d} За 1 день", callback_data=f"calendar:toggle:{event_id}:1d:{page}")
    kb.button(text=f"{r1h} За 1 час", callback_data=f"calendar:toggle:{event_id}:1h:{page}")
    kb.button(text="🚫 Отключить всё", callback_data=f"calendar:toggle:{event_id}:off:{page}")
    kb.button(text="⬅️ К событию", callback_data=f"calendar:event:{event_id}:{page}")
    kb.adjust(1)
    return kb.as_markup()


def my_reminders_keyboard(items: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for item in items[:15]:
        kb.button(text=item["title"], callback_data=f"calendar:event:{item['event_id']}:0")
    kb.button(text="📅 АБ| Афиша", callback_data="calendar:list:0")
    kb.button(text="🏠 В меню", callback_data="calendar:menu")
    kb.adjust(1)
    return kb.as_markup()
