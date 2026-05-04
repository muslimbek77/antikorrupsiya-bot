import asyncio
import logging
import sys
from typing import List

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramAPIError

from loader import dp, bot, db, ADMINS
from middlewares.throttling import ThrottlingMiddleware
from middlewares.checksub import BigBrother
from menucommands.set_bot_commands import set_default_commands
import handlers

# Logging konfiguratsiyasi
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def notify_admins(message: str, admins: List[int]) -> None:
    """Adminlarga xabar yuborish"""
    for admin_id in admins:
        try:
            await bot.send_message(chat_id=admin_id, text=message)
        except TelegramAPIError as e:
            logger.error(f"Failed to send message to admin {admin_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending message to admin {admin_id}: {e}")


@dp.startup()
async def on_startup_notify(bot: Bot) -> None:
    """Bot ishga tushganini xabarini yuborish"""
    try:
        logger.info("Bot starting up...")
        await notify_admins("✅ Bot ishga tushdi...", ADMINS)
        await set_default_commands(bot)
        db.create_table_users()
        db.create_table_channels()
        db.create_table_appeals()
    except Exception as e:
        logger.error(f"Error during startup: {e}", exc_info=True)


@dp.shutdown()
async def on_shutdown_notify(bot: Bot) -> None:
    """Bot ishdan to'xtadi xabarini yuborish"""
    try:
        logger.info("Bot shutting down...")
        await notify_admins("❌ Bot ishdan to'xtadi!", ADMINS)
    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)


async def main() -> None:
    """Botni ishga tushirish"""
    try:
        logger.info("Configuring middleware...")
        dp.message.middleware(ThrottlingMiddleware(slow_mode_delay=0.5))
        dp.message.middleware(BigBrother())
        
        logger.info("Starting bot polling...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        
    except Exception as e:
        logger.error(f"Critical error in main: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Critical error: {e}", exc_info=True)
        sys.exit(1)
