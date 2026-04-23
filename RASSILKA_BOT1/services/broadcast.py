from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import Message

from database.queries import get_all_users, set_block_status
from services.messaging import send_broadcast_copy


logger = logging.getLogger(__name__)
BROADCAST_DELAY = 0.05


async def broadcast_message(bot: Bot, admin_message: Message) -> dict[str, int]:
    users = get_all_users(active_only=True)
    stats = {"sent": 0, "failed": 0, "blocked": 0}

    for user in users:
        user_id = int(user["user_id"])
        try:
            await send_broadcast_copy(bot, user_id, admin_message)
            stats["sent"] += 1
            await asyncio.sleep(BROADCAST_DELAY)

        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            try:
                await send_broadcast_copy(bot, user_id, admin_message)
                stats["sent"] += 1
            except Exception:
                stats["failed"] += 1
                logger.exception("Broadcast retry failed for user_id=%s", user_id)

        except TelegramForbiddenError:
            set_block_status(user_id, True)
            stats["blocked"] += 1
            logger.warning("User blocked bot during broadcast: user_id=%s", user_id)

        except TelegramBadRequest:
            stats["failed"] += 1
            logger.exception("BadRequest during broadcast: user_id=%s", user_id)

        except Exception:
            stats["failed"] += 1
            logger.exception("Unexpected broadcast error: user_id=%s", user_id)

    return stats
