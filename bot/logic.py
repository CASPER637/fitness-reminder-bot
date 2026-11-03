"""Чистая логика без Telegram и базы данных — её легко тестировать."""
import math
import re
from datetime import date

from bot.config import DAY_END_HOUR, DAY_START_HOUR, WORKOUT_INTERVAL_DAYS

STEPS_PER_MINUTE = 100   # примерный темп быстрой ходьбы
MAX_STEPS = 100_000      # всё, что больше, считаем опечаткой

_STEPS_RE = re.compile(
    r"^\s*(\d+(?:[\s\u00a0]\d{3})*)(?:[.,](\d+))?\s*([кk])?\s*(?:шаг\w*)?\s*$",
    re.IGNORECASE,
)


def parse_steps(text: str) -> int | None:
    """Достаёт число шагов из сообщения: '8500', '8 500', '8.5к', '10k шагов'."""
    match = _STEPS_RE.match(text or "")
    if not match:
        return None
    whole, frac, k = match.groups()
    whole = re.sub(r"\s", "", whole)
    if k:
        value = float(f"{whole}.{frac}" if frac else whole) * 1000
    elif frac:
        return None  # «8.5» без «к» — непонятно, что имелось в виду
    else:
        value = float(whole)
    steps = round(value)
    return steps if 0 <= steps <= MAX_STEPS else None


def is_workout_due(last_workout: date | None, today: date,
                   interval: int = WORKOUT_INTERVAL_DAYS) -> bool:
    """Пора на тренировку, если с последней прошло не меньше interval дней."""
    if last_workout is None:
        return True
    return (today - last_workout).days >= interval


def expected_steps(goal: int, hour: float) -> int:
    """Сколько шагов «положено» к этому часу при равномерном темпе за день."""
    span = DAY_END_HOUR - DAY_START_HOUR
    fraction = min(max((hour - DAY_START_HOUR) / span, 0), 1)
    return round(goal * fraction)


def fmt(n: int) -> str:
    return f"{n:,}".replace(",", "\u00a0")


def _walk_time(steps_left: int) -> str:
    minutes = math.ceil(steps_left / STEPS_PER_MINUTE)
    if minutes < 60:
        return f"{minutes} мин"
    hours, rest = divmod(minutes, 60)
    return f"{hours} ч {rest} мин" if rest else f"{hours} ч"


def steps_reaction(steps: int, goal: int, hour: float) -> str:
    """Реакция бота на ответ о шагах с учётом времени суток."""
    if steps >= goal:
        extra = steps - goal
        if extra >= goal * 0.5:
            return (f"🏆 {fmt(steps)} шагов — это на {fmt(extra)} больше нормы! "
                    "Огонь, так держать!")
        return f"🎉 Норма выполнена: {fmt(steps)} из {fmt(goal)}! Отличная работа."

    left = goal - steps
    tail = f"Осталось {fmt(left)} шагов — это около {_walk_time(left)} быстрой ходьбы."
    ratio = steps / goal
    pace = steps - expected_steps(goal, hour)

    if ratio >= 0.8:
        return f"🔥 Почти у цели: {fmt(steps)} из {fmt(goal)}! {tail}"
    if pace >= 0:
        return f"👍 Идёшь по графику: {fmt(steps)} шагов. {tail}"
    if pace > -goal * 0.25:
        return (f"🙂 Чуть отстаёшь от графика ({fmt(steps)} шагов). "
                f"Пройдись при случае. {tail}")
    if hour >= 18:
        return (f"⚠️ Всего {fmt(steps)} шагов, а день заканчивается. "
                f"Выйди на прогулку сегодня! {tail}")
    return (f"🐢 Пока маловато: {fmt(steps)} шагов. "
            f"Время ещё есть — выйди размяться. {tail}")
