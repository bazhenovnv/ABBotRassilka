@PartnersTogether_bot
# Kolyan Bot v2 + АБ| Афиша

Полностью переработанная версия Telegram-бота на `aiogram 3`.

## Что уже есть

- модульная архитектура
- `BOT_TOKEN` вынесен в `.env`
- постоянная SQLite-база
- подписка / отписка
- постоянный blacklist
- постоянный cooldown
- поддержка: текст, фото, видео, документ, голосовое, аудио, видеосообщение
- ответ админа пользователю
- рассылка активным пользователям
- статистика
- экспорт пользователей в `TXT`
- логирование в консоль
- раздел **«АБ| Афиша»**
- список ближайших событий
- карточка события
- подписки на напоминания: за 3 дня / за 1 день / за 1 час / отключить
- раздел **«Мои напоминания»**
- автоматическая отправка напоминаний фоновым воркером
- сервисный слой `calendar_sync.py` для подключения к API календаря
- deep-link из календаря в бота на конкретное событие

## Новые таблицы SQLite

- `calendar_events`
- `user_event_reminders`
- `reminder_send_log`

## Новые файлы

- `handlers/calendar.py`
- `services/calendar_sync.py`
- `services/reminders.py`
- `database/calendar_queries.py`
- `keyboards/calendar.py`

## Доработанные файлы

- `app.py`
- `database/db.py`
- `handlers/user.py`
- `config/settings.py`
- `keyboards/user.py`

## Переменные окружения

- `BOT_TOKEN`
- `ADMIN_ID`
- `COOLDOWN_SECONDS=60`
- `DB_PATH=data/bot.sqlite3`
- `LOG_LEVEL=INFO`
- `CALENDAR_TIMEZONE=Europe/Moscow`
- `REMINDER_CHECK_INTERVAL_SECONDS=60`
- `CALENDAR_API_BASE_URL=http://localhost:4000/api`
- `CALENDAR_API_TIMEOUT_SECONDS=15`

## Установка

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
```

Создайте `.env` и укажите переменные окружения.

## Запуск

```bash
cd RASSILKA_BOT1
python app.py
```

## Интеграция с календарём

Бот рассчитан на работу с backend календаря по API.

Что используется:
- `GET /api/events?limit=30` — синхронизация ближайших событий
- `GET /api/events/id/:id` — открытие конкретного события по deep-link из календаря

Deep-link формат:
```text
https://t.me/<bot_username>?start=afisha_<uuid_события>
```
