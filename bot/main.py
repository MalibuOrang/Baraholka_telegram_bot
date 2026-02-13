import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.types import ErrorEvent

from bot.config import get_settings
from bot.database import crud
from bot.handlers import all_routers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    crud.configure(settings.db_path)
    await crud.init_db()

    bot = Bot(settings.bot_token, default=DefaultBotProperties())
    dp = Dispatcher()

    for r in all_routers:
        dp.include_router(r)

    @dp.errors()
    async def on_error(event: ErrorEvent) -> bool:
        log.exception("Unhandled error: %s", event.exception)
        return True

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await crud.close_db()


if __name__ == "__main__":
    asyncio.run(main())
