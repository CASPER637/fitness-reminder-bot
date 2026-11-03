"""Точка входа: python -m bot.main"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bot import config, reminders
from bot.db import Database
from bot.handlers import router


def setup_scheduler(bot: Bot, db: Database, tz) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=tz)
    args = [bot, db, tz]

    def cron(hm):
        return CronTrigger(hour=hm[0], minute=hm[1], timezone=tz)

    scheduler.add_job(reminders.morning_reminder, cron(config.MORNING_TIME), args=args)
    scheduler.add_job(reminders.workout_evening_nag, cron(config.WORKOUT_NAG_TIME), args=args)
    for hm in config.STEP_CHECK_TIMES:
        scheduler.add_job(reminders.ask_steps, cron(hm), args=args)
    scheduler.add_job(
        reminders.ask_steps, cron(config.FINAL_STEP_CHECK_TIME),
        args=args, kwargs={"final": True},
    )
    return scheduler


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    settings = config.load_settings()
    db = Database(settings.db_path)

    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp["db"] = db
    dp["tz"] = settings.timezone
    dp.include_router(router)

    scheduler = setup_scheduler(bot, db, settings.timezone)
    scheduler.start()
    logging.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
