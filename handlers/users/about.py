import logging
from aiogram.types import Message
from aiogram.filters import Command
from loader import dp

logger = logging.getLogger(__name__)


@dp.message(Command("about"))
async def about_commands(message: Message) -> None:
    """Bot haqida malumot"""
    about_text = (
        "ℹ️ <b>Bot haqida</b>\n\n"
        "Ushbu bot korrupsiyaga oid murojaatlarni qabul qilish, tahlil qilish "
        "va rahbariyat uchun hisobot tayyorlash uchun moslashtirildi.\n\n"
        "Asosiy imkoniyatlar:\n"
        "• murojaatlarni yig'ish\n"
        "• AI asosida toifalash va xavf bahosi\n"
        "• admin uchun statistika va PDF hisobot"
    )
    await message.answer(about_text, parse_mode="HTML", disable_web_page_preview=True)
    logger.info(f"About requested by user {message.from_user.id}")
