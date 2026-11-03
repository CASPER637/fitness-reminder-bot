"""Обработчики команд, кнопок и ответов пользователя."""
from datetime import timedelta
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from bot.config import STEP_GOAL, now_in, today_in
from bot.db import Database
from bot.logic import fmt, parse_steps, steps_reaction

router = Router()

HELP_TEXT = (
    "Я напоминаю про тренировки (через день) и считаю шаги (норма {goal}).\n\n"
    "Просто пришли число шагов, например <code>7500</code> или <code>8.5к</code> — "
    "я отвечу, как у тебя дела.\n\n"
    "Команды:\n"
    "/steps — шаги за сегодня\n"
    "/workout — отметить, что тренировка сделана\n"
    "/stats — статистика за неделю\n"
    "/pause — выключить напоминания\n"
    "/resume — включить обратно"
)


@router.message(CommandStart())
async def cmd_start(message: Message, db: Database) -> None:
    db.add_user(message.chat.id)
    await message.answer(
        "Привет! 👋 Я бот-напоминалка.\n\n" + HELP_TEXT.format(goal=fmt(STEP_GOAL))
        + "\n\nПервая тренировка — сегодня 💪"
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT.format(goal=fmt(STEP_GOAL)))


@router.message(Command("pause"))
async def cmd_pause(message: Message, db: Database) -> None:
    db.set_paused(message.chat.id, True)
    await message.answer("⏸ Напоминания выключены. Включить обратно: /resume")


@router.message(Command("resume"))
async def cmd_resume(message: Message, db: Database) -> None:
    db.add_user(message.chat.id)
    await message.answer("▶️ Напоминания снова включены.")


@router.message(Command("workout"))
async def cmd_workout(message: Message, db: Database, tz: ZoneInfo) -> None:
    db.log_workout(message.chat.id, today_in(tz))
    await message.answer("✅ Тренировка записана. Следующая — через 2 дня.")


@router.message(Command("steps"))
async def cmd_steps(message: Message, db: Database, tz: ZoneInfo) -> None:
    steps = db.get_steps(message.chat.id, today_in(tz))
    if steps is None:
        await message.answer("Сегодня шаги ещё не записаны. Пришли число!")
    else:
        await message.answer(f"Сегодня: {fmt(steps)} из {fmt(STEP_GOAL)} шагов.")


@router.message(Command("stats"))
async def cmd_stats(message: Message, db: Database, tz: ZoneInfo) -> None:
    today = today_in(tz)
    lines = ["📊 <b>Шаги за 7 дней</b>"]
    for day, steps in db.steps_history(message.chat.id, today, 7):
        if steps is None:
            mark, value = "▫️", "нет данных"
        else:
            mark, value = ("✅" if steps >= STEP_GOAL else "❌"), fmt(steps)
        lines.append(f"{mark} {day:%d.%m}: {value}")
    workouts = db.count_workouts(message.chat.id, today - timedelta(days=13))
    lines.append(f"\n🏋️ Тренировок за 14 дней: {workouts}")
    await message.answer("\n".join(lines))


@router.callback_query(F.data == "workout:done")
async def cb_workout_done(callback: CallbackQuery, db: Database, tz: ZoneInfo) -> None:
    db.log_workout(callback.message.chat.id, today_in(tz))
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("💪 Молодец! Тренировка записана, следующая — через 2 дня.")
    await callback.answer()


@router.callback_query(F.data == "workout:skip")
async def cb_workout_skip(callback: CallbackQuery, db: Database, tz: ZoneInfo) -> None:
    db.set_skip(callback.message.chat.id, today_in(tz))
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "Ок, сегодня не беспокою. Но завтра напомню снова — график важнее настроения 😉"
    )
    await callback.answer()


@router.message(F.text)
async def on_text(message: Message, db: Database, tz: ZoneInfo) -> None:
    steps = parse_steps(message.text)
    if steps is None:
        await message.answer(
            "Не понял 🤔 Пришли число шагов, например <code>7500</code> или <code>8.5к</code>. "
            "Список команд: /help"
        )
        return
    db.add_user(message.chat.id)  # на случай, если не нажимали /start
    now = now_in(tz)
    db.set_steps(message.chat.id, now.date(), steps)
    await message.answer(steps_reaction(steps, STEP_GOAL, now.hour + now.minute / 60))
