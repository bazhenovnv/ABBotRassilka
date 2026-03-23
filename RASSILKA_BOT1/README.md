

@PartnersTogether_bot

# Kolyan Bot v2

Полностью переработанная версия Telegram-бота на `aiogram 3`.

## Что уже сделано

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
- экспорт пользователей в `CSV` и `TXT`
- логирование в консоль и `logs/bot.log`

## Важно

Старый токен был засвечен в исходниках. Его нужно отозвать через BotFather и выпустить новый.

## Установка

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env




Запуск бота, такой:

1. cd ABBotRassilka
python -m venv venv

Windows:
в CMD:
2. venv\Scripts\activate

3. pip install -r requirements.txt

После этого запуск:

4. python app.py