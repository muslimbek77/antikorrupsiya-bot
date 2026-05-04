import logging
from typing import List, Tuple
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

logger = logging.getLogger(__name__)

# Admin menyu tugmalari
admin_button = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Foydalanuvchilar soni"),
            KeyboardButton(text="Reklama yuborish"),
        ],
        [
            KeyboardButton(text="⛓ Kanallar ro'yxati"),
        ],
        [
            KeyboardButton(text="➕ Kanal qo'shish"),
            KeyboardButton(text="➖ Kanal o'chirish"),
        ],
        [
            KeyboardButton(text="📈 Murojaatlar statistikasi"),
            KeyboardButton(text="🆕 So'nggi murojaatlar"),
        ],
        [
            KeyboardButton(text="📄 PDF hisobot"),
        ],
    ],
    resize_keyboard=True,
    input_field_placeholder="📋 Menudan birini tanlang"
)


def inline_wars_btn(channels: List[Tuple]) -> InlineKeyboardMarkup:
    """
    Kanallarni tanlash uchun inline buttons yaratish
    
    Args:
        channels: Kanallar ro'yxati
    
    Returns:
        InlineKeyboardMarkup: Inline keyboard markup
    """
    if not channels:
        logger.warning("No channels provided for inline buttons")
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="↩️ Orqaga", callback_data="back_admin")
        ]])
    
    # Tugmalar soniga ko'ra qatorni aniqlash
    button_count = len(channels)
    buttons_per_row = 3 if button_count <= 6 else 4 if button_count <= 8 else 6
    
    # Tugmalarni yaratish
    buttons = []
    for idx, channel in enumerate(channels, 1):
        channel_id = channel[0]
        buttons.append(InlineKeyboardButton(
            text=f"#{idx}",
            callback_data=str(channel_id)
        ))
    
    # Qatorlarga bo'lish
    keyboard = []
    for i in range(0, len(buttons), buttons_per_row):
        keyboard.append(buttons[i:i + buttons_per_row])
    
    # Orqaga tugmasi
    keyboard.append([
        InlineKeyboardButton(text="↩️ Orqaga", callback_data="back_admin")
    ])
    
    logger.debug(f"Created inline keyboard with {len(buttons)} channels")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def channel_add_options() -> InlineKeyboardMarkup:
    """Kanal qo'shish usullarini tanlash tugmalari"""
    buttons = [
        [InlineKeyboardButton(text="📌 Postni forward qilish", callback_data="add_forward")],
        [InlineKeyboardButton(text="🔢 ID yuborish (-100...)", callback_data="add_id")],
        [InlineKeyboardButton(text="📝 Username yuborish (@kanal)", callback_data="add_username")],
    ]
    logger.debug("Channel add options keyboard created")
    return InlineKeyboardMarkup(inline_keyboard=buttons)
