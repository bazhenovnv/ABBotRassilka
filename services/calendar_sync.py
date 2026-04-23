from __future__ import annotations

import logging
from collections.abc import Iterable

import requests

from config.settings import settings
from database.calendar_queries import get_event_by_external_id, upsert_calendar_event


logger = logging.getLogger(__name__)


class CalendarSyncService:
    """
    Сервисный слой интеграции с календарем «АБ| Афиша».
    - хранит локальную SQLite-копию ближайших событий для бота;
    - подтягивает события из API календаря;
    - умеет адресно синхронизировать одно событие по его UUID для deep-link.
    """

    def __init__(self) -> None:
        self.base_url = settings.calendar_api_base_url
        self.timeout = settings.calendar_api_timeout_seconds

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _map_remote_event(self, event: dict) -> dict:
        external_id = f"calendar_event:{event['id']}"
        description = event.get("descriptionFull") or event.get("descriptionShort") or event.get("description")
        return {
            "external_id": external_id,
            "title": event["title"],
            "description": description,
            "location": event.get("location"),
            "starts_at": event["startAt"],
            "ends_at": event.get("endAt"),
            "source_url": event.get("sourceUrl"),
            "is_active": bool(event.get("published", True)),
        }

    def sync_events(self, events: Iterable[dict]) -> int:
        count = 0
        for event in events:
            payload = self._map_remote_event(event) if "startAt" in event else event
            upsert_calendar_event(
                external_id=payload.get("external_id"),
                title=payload["title"],
                description=payload.get("description"),
                location=payload.get("location"),
                starts_at=payload["starts_at"],
                ends_at=payload.get("ends_at"),
                source_url=payload.get("source_url"),
                is_active=payload.get("is_active", True),
            )
            count += 1
        return count

    def fetch_upcoming_events(self, limit: int = 30) -> list[dict]:
        response = requests.get(
            self._url(f"/events?limit={limit}"),
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("API календаря вернул неожиданный формат списка событий")
        return payload

    def sync_upcoming_events(self, limit: int = 30) -> int:
        events = self.fetch_upcoming_events(limit=limit)
        return self.sync_events(events)

    def fetch_event_by_public_id(self, event_id: str) -> dict:
        response = requests.get(
            self._url(f"/events/id/{event_id}"),
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("API календаря вернул неожиданный формат карточки события")
        return payload

    def sync_event_by_public_id(self, event_id: str) -> dict:
        remote = self.fetch_event_by_public_id(event_id)
        mapped = self._map_remote_event(remote)
        upsert_calendar_event(**mapped)
        local = get_event_by_external_id(mapped["external_id"])
        if not local:
            raise LookupError(f"Событие {event_id} не удалось сохранить локально")
        return local


calendar_sync_service = CalendarSyncService()
