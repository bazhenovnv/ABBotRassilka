import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

BASE_DIR = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass


def _to_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None and str(value).strip() != "" else default
    except (TypeError, ValueError):
        return default


@dataclass
class Settings:
    bot_token: str
    admin_id: int
    cooldown_seconds: int
    db_path: Path
    log_level: str
    calendar_timezone_name: str
    reminder_check_interval_seconds: int
    calendar_api_base_url: str
    calendar_api_timeout_seconds: int

    @property
    def calendar_timezone(self) -> ZoneInfo:
        try:
            return ZoneInfo(self.calendar_timezone_name)
        except ZoneInfoNotFoundError:
            return ZoneInfo("UTC")



def load_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    admin_id = _to_int(os.getenv("ADMIN_ID"), 0)
    cooldown_seconds = _to_int(os.getenv("COOLDOWN_SECONDS"), 60)

    db_path_env = os.getenv("DB_PATH", "").strip()
    if db_path_env:
        db_path = Path(db_path_env)
        if not db_path.is_absolute():
            db_path = BASE_DIR / db_path
    else:
        db_path = BASE_DIR / "data" / "bot.sqlite3"

    log_level = os.getenv("LOG_LEVEL", "INFO").strip() or "INFO"
    calendar_timezone_name = os.getenv("CALENDAR_TIMEZONE", "Europe/Moscow").strip() or "Europe/Moscow"
    reminder_check_interval_seconds = _to_int(os.getenv("REMINDER_CHECK_INTERVAL_SECONDS"), 60)
    calendar_api_base_url = (os.getenv("CALENDAR_API_BASE_URL", "http://localhost:4000/api").strip() or "http://localhost:4000/api").rstrip("/")
    calendar_api_timeout_seconds = _to_int(os.getenv("CALENDAR_API_TIMEOUT_SECONDS"), 15)

    if not bot_token:
        raise ValueError("Не задан BOT_TOKEN в переменных окружения")

    if not admin_id:
        raise ValueError("Не задан ADMIN_ID в переменных окружения")

    return Settings(
        bot_token=bot_token,
        admin_id=admin_id,
        cooldown_seconds=cooldown_seconds,
        db_path=db_path,
        log_level=log_level,
        calendar_timezone_name=calendar_timezone_name,
        reminder_check_interval_seconds=reminder_check_interval_seconds,
        calendar_api_base_url=calendar_api_base_url,
        calendar_api_timeout_seconds=calendar_api_timeout_seconds,
    )


settings = load_settings()
