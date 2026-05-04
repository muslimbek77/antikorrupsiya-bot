import logging

from aiogram import F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from keyboard_buttons.user_keyboard import main_menu
from loader import ADMINS, bot, db, dp
from services.ai_analysis import analyze_appeal
from states.reklama import AppealState

logger = logging.getLogger(__name__)


@dp.message(CommandStart())
async def start_command(message: Message) -> None:
    """Botni start qilish va asosiy menyuni ko'rsatish"""
    full_name = message.from_user.full_name or "Unknown"
    telegram_id = message.from_user.id
    db.add_user(full_name=full_name, telegram_id=telegram_id)

    await message.answer(
        text=(
            "Assalomu alaykum.\n\n"
            "Bu bot korrupsiyaga oid murojaatlarni qabul qiladi, ularni avtomatik tahlil qiladi "
            "va mas'ullarga yuboradi. Murojaat yuborish uchun menyudan foydalaning."
        ),
        reply_markup=main_menu,
    )
    logger.info("Start requested by %s", telegram_id)


@dp.message(F.text == "ℹ️ Yordam")
async def show_help(message: Message) -> None:
    await message.answer(
        "Murojaat yuborish uchun `📝 Murojaat yuborish` tugmasini bosing.\n"
        "Bot F.I.O, telefon va murojaat matnini oladi, keyin AI tahlil qilib adminlarga yuboradi."
    )


@dp.message(F.text == "📝 Murojaat yuborish")
async def appeal_start(message: Message, state: FSMContext) -> None:
    await state.set_state(AppealState.full_name)
    await message.answer("F.I.O ni yuboring:")


@dp.message(AppealState.full_name)
async def appeal_full_name(message: Message, state: FSMContext) -> None:
    await state.update_data(full_name=message.text.strip())
    await state.set_state(AppealState.phone)
    await message.answer("Telefon raqamingizni yuboring:")


@dp.message(AppealState.phone)
async def appeal_phone(message: Message, state: FSMContext) -> None:
    await state.update_data(phone=message.text.strip())
    await state.set_state(AppealState.organization)
    await message.answer("Tashkilot yoki bo'lim nomini yuboring (agar bo'lmasa `-` yuboring):")


@dp.message(AppealState.organization)
async def appeal_organization(message: Message, state: FSMContext) -> None:
    organization = message.text.strip()
    await state.update_data(organization="" if organization == "-" else organization)
    await state.set_state(AppealState.message)
    await message.answer("Murojaat matnini batafsil yuboring:")


@dp.message(AppealState.message)
async def appeal_message(message: Message, state: FSMContext) -> None:
    message_text = (message.text or "").strip()
    if len(message_text) < 20:
        await message.answer("Murojaat matni juda qisqa. Iltimos, holatni batafsilroq yozing.")
        return

    data = await state.get_data()
    analysis = analyze_appeal(message_text)
    appeal_id = db.add_appeal(
        user_id=message.from_user.id,
        full_name=data["full_name"],
        phone=data["phone"],
        organization=data.get("organization", ""),
        message_text=message_text,
        analysis=analysis,
    )

    await state.clear()
    await message.answer(
        text=(
            f"Murojaatingiz qabul qilindi.\n\n"
            f"ID: #{appeal_id}\n"
            f"Toifa: {analysis['category']}\n"
            f"Xavf darajasi: {analysis['risk_level']}\n"
            f"Yo'naltirish: {analysis['route_to']}"
        ),
        reply_markup=main_menu,
    )

    organization_name = data.get("organization") or "ko'rsatilmagan"
    admin_text = (
        f"Yangi murojaat #{appeal_id}\n\n"
        f"F.I.O: {data['full_name']}\n"
        f"Telefon: {data['phone']}\n"
        f"Tashkilot: {organization_name}\n"
        f"Toifa: {analysis['category']}\n"
        f"Xavf: {analysis['risk_level']}\n"
        f"Muhimlik: {analysis['priority']}\n"
        f"Yo'naltirish: {analysis['route_to']}\n"
        f"Kalit so'zlar: {analysis['keywords']}\n\n"
        f"Murojaat:\n{message_text}"
    )
    for admin_id in ADMINS:
        try:
            await bot.send_message(admin_id, admin_text)
        except Exception as error:
            logger.error("Failed to notify admin %s: %s", admin_id, error)


@dp.message(F.text == "📊 Mening holatim")
async def my_status(message: Message) -> None:
    appeals = db.get_user_appeals(message.from_user.id)
    if not appeals:
        await message.answer("Sizda hali murojaatlar mavjud emas.", reply_markup=main_menu)
        return

    lines = ["So'nggi murojaatlaringiz:"]
    for appeal_id, category, risk_level, status, created_at in appeals:
        lines.append(
            f"#{appeal_id} | {category} | {risk_level} xavf | {status} | {created_at}"
        )
    await message.answer("\n".join(lines), reply_markup=main_menu)
