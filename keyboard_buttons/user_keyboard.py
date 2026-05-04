from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Murojaat yuborish")],
        [KeyboardButton(text="📊 Mening holatim"), KeyboardButton(text="ℹ️ Yordam")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Kerakli bo'limni tanlang",
)
