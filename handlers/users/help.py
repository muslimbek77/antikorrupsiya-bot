import logging
from aiogram.types import Message
from aiogram.filters import Command
from loader import dp

logger = logging.getLogger(__name__)


@dp.message(Command("help"))
async def help_commands(message: Message) -> None:
    """Yordam komandasi"""
    help_text = (
        "🆘 <b>Yordam</b>\n\n"
        "Bot quyidagi xizmatlarni taqdim etadi:\n\n"
        "• 📝 Korrupsiyaga oid murojaat yuborish\n"
        "• 🤖 Murojaatni avtomatik AI tahlil qilish\n"
        "• 📊 Murojaat holatini kuzatish\n"
        "• 📄 Admin uchun statistik PDF hisobot yaratish\n\n"
        "Boshlash uchun /start yoki asosiy menyudan foydalaning."
    )
    await message.answer(help_text, parse_mode="HTML")
    logger.info(f"Help requested by user {message.from_user.id}")
