from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


# путь к корню проекта
BASE_DIR = Path(__file__).resolve().parent.parent

# загрузка .env
load_dotenv(BASE_DIR / ".env", override=True)


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_id: int
    cooldown_seconds: int
    db_path: Path
    log_level: str


settings = Settings(
    bot_token=os.getenv("BOT_TOKEN", "").strip(),
    admin_id=int(os.getenv("ADMIN_ID", "0")),
    cooldown_seconds=int(os.getenv("COOLDOWN_SECONDS", "60")),
    db_path=BASE_DIR / os.getenv("DB_PATH", "data/bot.sqlite3"),
    log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
)

# проверки
if not settings.bot_token:
    raise RuntimeError("BOT_TOKEN не найден. Проверьте файл .env")

if settings.admin_id <= 0:
    raise RuntimeError("ADMIN_ID не задан или некорректен")


# диагностика (можно потом удалить)
print("BOT TOKEN PREFIX:", settings.bot_token[:15])
print("BOT TOKEN LENGTH:", len(settings.bot_token))
print("ADMIN_ID:", settings.admin_id)