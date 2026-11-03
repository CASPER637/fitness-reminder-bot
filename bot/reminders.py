"""Задачи по расписанию: утро, напоминания о тренировке и вопросы про шаги."""
import logging
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.config import STEP_GOAL, now_in, today_in
from bot.db import Database
from bot.logic import fmt, is_workout_due

log = logging.getLogger(__name__)


def workout_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="Сходил ✅", callback_data="workout:done"),
            InlineKeyboardButton(text="Сегодня пропущу ❌", callback_data="workout:skip"),
        ]]
    )


async def _safe_send(bot: Bot, db: Database, chat_id: int, text: str, **kwargs) -> None:
    try:
        await bot.send_message(chat_id, text, **kwargs)
    except TelegramForbiddenError:
        # пользователь заблокировал бота — перестаём ему писать
        log.warning("Chat %s blocked the bot, pausing", chat_id)
        db.set_paused(chat_id, True)
    except Exception:
        log.exception("Failed to send message to %s", chat_id)


def _workout_pending(db: Database, chat_id: int, tz: ZoneInfo) -> bool:
    today = today_in(tz)
    if db.skipped_on(chat_id, today):
        return False
    last = db.last_workout(chat_id)
    return is_workout_due(last, today)


async def morning_reminder(bot: Bot, db: Database, tz: ZoneInfo) -> None:
    for chat_id in db.active_users():
        await _safe_send(
            bot, db, chat_id,
            f"☀️ Доброе утро! Цель на сегодня — {fmt(STEP_GOAL)} шагов. "
            "В течение дня я спрошу, как идут дела.",
        )
        if _workout_pending(db, chat_id, tz):
            await _safe_send(
                bot, db, chat_id,
                "🏋️ Сегодня день тренировки! Не забудь сходить.",
                reply_markup=workout_keyboard(),
            )


async def workout_evening_nag(bot: Bot, db: Database, tz: ZoneInfo) -> None:
    for chat_id in db.active_users():
        if _workout_pending(db, chat_id, tz):
            await _safe_send(
                bot, db, chat_id,
                "🏋️ Ты ещё не отметил тренировку. Есть время сходить сегодня!",
                reply_markup=workout_keyboard(),
            )


async def ask_steps(bot: Bot, db: Database, tz: ZoneInfo, final: bool = False) -> None:
    today = today_in(tz)
    for chat_id in db.active_users():
        steps = db.get_steps(chat_id, today)
        if steps is not None and steps >= STEP_GOAL:
            continue  # норма уже выполнена — не надоедаем
        if final:
            text = ("🌙 День подходит к концу. Сколько шагов в итоге? "
                    "Напиши число, например 8500.")
        else:
            text = "🚶 Сколько шагов уже прошёл? Ответь числом, например 6300."
        await _safe_send(bot, db, chat_id, text)
