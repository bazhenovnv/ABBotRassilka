import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config.settings import settings
from database.db import init_db
from handlers.admin import admin_router
from handlers.common import common_router
from handlers.user import user_router
from utils.logger import setup_logging


async def main() -> None:
    setup_logging(settings.log_level)
    init_db()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(common_router)
    dp.include_router(admin_router)
    dp.include_router(user_router)

    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())