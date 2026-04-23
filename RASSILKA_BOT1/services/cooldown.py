from __future__ import annotations

import time

from config.settings import settings
from database.queries import clear_cooldown, cleanup_expired_cooldowns, get_cooldown_until, set_cooldown


def get_remaining_seconds(user_id: int) -> int:
    cleanup_expired_cooldowns(int(time.time()))
    until_ts = get_cooldown_until(user_id)
    if not until_ts:
        return 0

    remaining = until_ts - int(time.time())
    if remaining <= 0:
        clear_cooldown(user_id)
        return 0

    return remaining


def start_cooldown(user_id: int) -> int:
    until_ts = int(time.time()) + settings.cooldown_seconds
    set_cooldown(user_id, until_ts)
    return until_ts
