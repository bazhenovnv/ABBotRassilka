from __future__ import annotations

from database.queries import get_user, set_subscription, upsert_user


def subscribe_user(user_id: int, username: str | None, first_name: str | None, full_name: str | None) -> None:
    upsert_user(user_id, username, first_name, full_name)
    set_subscription(user_id, True)


def unsubscribe_user(user_id: int) -> None:
    if get_user(user_id):
        set_subscription(user_id, False)
