import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError

from config.settings import settings
from database.db import init_db
from handlers.admin import admin_router
from handlers.calendar import calendar_router
from handlers.common import common_router
from handlers.user import user_router
from services.reminders import reminder_worker


async def main():
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    init_db()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()
    dp.include_router(common_router)
    dp.include_router(admin_router)
    dp.include_router(calendar_router)
    dp.include_router(user_router)

    while True:
        reminder_task = None
        try:
            reminder_task = asyncio.create_task(reminder_worker(bot))
            logging.info("Запуск polling...")
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        except TelegramNetworkError as e:
            logging.error("Ошибка сети при подключении к Telegram: %s", e)
            logging.info("Повторная попытка через 15 секунд...")
            await asyncio.sleep(15)
        except Exception as e:
            logging.exception("Критическая ошибка запуска бота: %s", e)
            logging.info("Повторная попытка через 15 секунд...")
            await asyncio.sleep(15)
        finally:
            if reminder_task:
                reminder_task.cancel()
                try:
                    await reminder_task
                except asyncio.CancelledError:
                    pass


if __name__ == "__main__":
    asyncio.run(main())
