"""Настройки бота: токен из окружения и параметры расписания."""
import os
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

# ---- Цели ----
STEP_GOAL = 10_000            # дневная норма шагов
WORKOUT_INTERVAL_DAYS = 2     # тренировка через день

# ---- Расписание (часы, минуты по местному времени) ----
MORNING_TIME = (9, 0)                                # утреннее напоминание
WORKOUT_NAG_TIME = (19, 0)                           # повторное напоминание о тренировке
STEP_CHECK_TIMES = [(12, 0), (15, 0), (18, 0)]       # вопросы «сколько шагов?»
FINAL_STEP_CHECK_TIME = (21, 30)                     # последний вопрос за день

# Границы «дня» для оценки темпа ходьбы
DAY_START_HOUR = 8
DAY_END_HOUR = 22


@dataclass(frozen=True)
class Settings:
    bot_token: str
    timezone: ZoneInfo
    db_path: str


def load_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "Не задан BOT_TOKEN. Создайте файл .env по образцу .env.example"
        )
    return Settings(
        bot_token=token,
        timezone=ZoneInfo(os.getenv("TIMEZONE", "Europe/Moscow")),
        db_path=os.getenv("DB_PATH", "data/bot.db"),
    )


def now_in(tz: ZoneInfo) -> datetime:
    return datetime.now(tz)


def today_in(tz: ZoneInfo) -> date:
    return now_in(tz).date()
