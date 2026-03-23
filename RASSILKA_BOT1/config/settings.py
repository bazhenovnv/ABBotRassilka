import os
from dataclasses import dataclass
from pathlib import Path

# Базовая папка проекта
BASE_DIR = Path(__file__).resolve().parent.parent

# Делаем python-dotenv необязательным
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
    db_path: str
    log_level: str


def load_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    admin_id = _to_int(os.getenv("ADMIN_ID"), 0)
    cooldown_seconds = _to_int(os.getenv("COOLDOWN_SECONDS"), 60)
    db_path = os.getenv("DB_PATH", str(BASE_DIR / "data" / "bot.sqlite3")).strip()
    log_level = os.getenv("LOG_LEVEL", "INFO").strip() or "INFO"

    if not bot_token:
        raise ValueError("Не задан BOT_TOKEN в переменных окружения")

    if not admin_id:
        raise ValueError("Не задан ADMIN_ID в переменных окружения")

    return Settings(
        bot_token=bot_token,
        admin_id=admin_id,
        cooldown_seconds=cooldown_seconds,
        db_path=db_path or str(BASE_DIR / "data" / "bot.sqlite3"),
        log_level=log_level,
    )


settings = load_settings()
