import asyncio
import logging
import os

from aiogram import F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramAPIError

from loader import bot, db, dp, ADMINS
from filters.admin import IsBotAdminFilter
from states.reklama import Adverts, ChannelState, DelChannelState
from keyboard_buttons import admin_keyboard
from services.pdf_report import generate_statistics_pdf

logger = logging.getLogger(__name__)

ADVERT_DELAY = 0.01  # Reklama yuborishda kechikish (Telegram API chekloviga ko'ra)


@dp.message(Command("admin"), IsBotAdminFilter(ADMINS))
async def is_admin(message: Message) -> None:
    """Admin menyusini ochish"""
    logger.info(f"Admin menu requested by {message.from_user.id}")
    await message.answer(
        text="🔐 Admin menyu",
        reply_markup=admin_keyboard.admin_button
    )


@dp.message(F.text == "Foydalanuvchilar soni", IsBotAdminFilter(ADMINS))
async def users_count(message: Message) -> None:
    """Foydalanuvchilar sonini ko'rsatish"""
    try:
        count = db.count_users()
        text = f"👥 Botimizda <b>{count}</b> ta foydalanuvchi bor"
        await message.answer(text=text, parse_mode="HTML")
        logger.info(f"User count requested: {count}")
    except Exception as e:
        logger.error(f"Failed to get user count: {e}")
        await message.answer("❌ Xato: Foydalanuvchilar sonini olib bo'lmadi")


@dp.message(F.text == "Reklama yuborish", IsBotAdminFilter(ADMINS))
async def advert_dp(message: Message, state: FSMContext) -> None:
    """Reklama yuborish holatiga o'tish"""
    await state.set_state(Adverts.adverts)
    logger.info(f"Advert mode started by admin {message.from_user.id}")
    await message.answer(
        text="📢 Reklama yuborishingiz mumkin!\n\n"
             "Iltimos, reklama mazmunini yuboring (matn, rasm, video yoki fayl):"
    )


@dp.message(Adverts.adverts)
async def send_advert(message: Message, state: FSMContext) -> None:
    """Reklama yuborish"""
    message_id = message.message_id
    from_chat_id = message.from_user.id
    users = db.all_users_id()
    
    if not users:
        await message.answer("⚠️ Foydalanuvchilar mavjud emas")
        await state.clear()
        return
    
    status_msg = await message.answer("⏳ Reklama yuborilmoqda...")
    count = 0
    failed = 0
    
    try:
        for user in users:
            try:
                await bot.copy_message(
                    chat_id=user[0],
                    from_chat_id=from_chat_id,
                    message_id=message_id
                )
                count += 1
            except TelegramAPIError as e:
                logger.warning(f"Failed to send advert to user {user[0]}: {e}")
                failed += 1
            except Exception as e:
                logger.error(f"Unexpected error sending to {user[0]}: {e}")
                failed += 1
            
            await asyncio.sleep(ADVERT_DELAY)
        
        result_text = (
            f"📊 Reklama yuborish tugadi!\n\n"
            f"✅ Yuborildi: <b>{count}</b>\n"
            f"❌ Xato: <b>{failed}</b>"
        )
        await status_msg.edit_text(result_text, parse_mode="HTML")
        logger.info(f"Advert sent to {count} users, {failed} failed")
        
    except Exception as e:
        logger.error(f"Error during advert send: {e}")
        await status_msg.edit_text("❌ Reklama yuborishda xato yuz berdi")
    
    await state.clear()


@dp.message(F.text == "⛓ Kanallar ro'yxati", IsBotAdminFilter(ADMINS))
async def show_channels(message: Message) -> None:
    """Kanallar ro'yxatini ko'rsatish"""
    try:
        channels = db.select_all_channels()
        
        if not channels:
            await message.answer("⚠️ Kanal mavjud emas")
            return
        
        text = "⛓ <b>Kanallar ro'yxati:</b>\n\n"
        for idx, (channel_id, channel_name, channel_link) in enumerate(channels, 1):
            text += (
                f"<b>{idx}.</b> {channel_name}\n"
                f"🔗 <a href='{channel_link}'>Link</a>\n\n"
            )
        
        await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)
        logger.info(f"Channels list requested: {len(channels)} channels")
        
    except Exception as e:
        logger.error(f"Failed to show channels: {e}")
        await message.answer("❌ Kanallar ro'yxatini olib bo'lmadi")


@dp.message(F.text == "➕ Kanal qo'shish", IsBotAdminFilter(ADMINS))
async def add_channel_start(message: Message, state: FSMContext) -> None:
    """Kanal qo'shishni boshlash"""
    await state.set_state(ChannelState.kanal_qoshish)
    logger.info(f"Add channel started by admin {message.from_user.id}")
    await message.answer(
        "➕ Kanalni qo'shish usulini tanlang:",
        reply_markup=admin_keyboard.channel_add_options(),
    )


@dp.message(ChannelState.kanal_qoshish, IsBotAdminFilter(ADMINS))
async def add_channel(message: Message, state: FSMContext) -> None:
    """Kanalni qo'shish"""
    try:
        channel_id = None
        channel_name = None
        invite_link = None
        
        # Forwarded post orqali kanal ID olish
        if message.forward_from_chat:
            channel_id = message.forward_from_chat.id
            channel_name = message.forward_from_chat.title
        
        # Chat ID yoki username orqali
        elif message.text:
            chat = await bot.get_chat(message.text)
            channel_id = chat.id
            channel_name = chat.title or chat.full_name
        else:
            await message.answer("❌ Nimadir xato ketti. Iltimos, qaytadan urinib ko'ring")
            await state.clear()
            return
        
        # Bot kanal azo'dligini tekshirish
        try:
            me = await bot.me()
            await bot.get_chat_member(channel_id, me.id)
        except TelegramAPIError:
            raise Exception("Bot kanal yoki guruhga qo'shilmagan")
        
        # Invite link olish
        chat = await bot.get_chat(channel_id)
        invite_link = await chat.export_invite_link()
        
        # Bazaga saqlash
        db.add_channel(channel_id, channel_name, invite_link)
        
        text = (
            f"✅ Kanal qo'shildi!\n\n"
            f"📛 Nomi: <b>{channel_name}</b>\n"
            f"🔗 <a href='{invite_link}'>Kanal linki</a>"
        )
        await message.answer(text, reply_markup=admin_keyboard.admin_button, parse_mode="HTML")
        logger.info(f"Channel added: {channel_id} - {channel_name}")
        
    except Exception as err:
        logger.error(f"Failed to add channel: {err}")
        await message.answer(
            f"❌ Xato: {err}\n\n"
            "Qadamlar:\n"
            "1️⃣ Botni kanal yoki guruhga qo'shing\n"
            "2️⃣ Botga admin huquqlari bering\n"
            "3️⃣ Qaytadan urinib ko'ring",
            reply_markup=admin_keyboard.admin_button
        )
    
    await state.clear()


@dp.callback_query(F.data.in_({"add_forward", "add_id", "add_username"}), IsBotAdminFilter(ADMINS))
async def channel_add_help(call: CallbackQuery, state: FSMContext) -> None:
    """Kanal qo'shish yo'riqnomasi"""
    await state.set_state(ChannelState.kanal_qoshish)
    
    instructions = {
        "add_forward": "📌 Kanaldan biror postni <b>forward</b> qiling.",
        "add_id": "🔢 Kanal ID sini yuboring (masalan: -1001234567890).",
        "add_username": "📝 Kanal username yuboring (masalan: @mychannel).",
    }
    
    await call.message.answer(instructions.get(call.data, "Ma'lumot yuboring."), parse_mode="HTML")
    await call.answer()


@dp.message(F.text == "➖ Kanal o'chirish", IsBotAdminFilter(ADMINS))
async def delete_channel_start(message: Message, state: FSMContext) -> None:
    """Kanal o'chirishni boshlash"""
    try:
        channels = db.select_all_channels()
        
        if not channels:
            await message.answer("⚠️ O'chirish uchun kanal mavjud emas")
            return
        
        await state.set_state(DelChannelState.delete_channel)
        text = "➖ <b>O'chirilishi kerak bo'lgan kanallarni tanlang:</b>\n\n"
        
        for idx, (channel_id, channel_name, channel_link) in enumerate(channels, 1):
            text += f"{idx}. {channel_name}\n"
        
        await message.answer(
            text,
            reply_markup=admin_keyboard.inline_wars_btn(channels),
            parse_mode="HTML"
        )
        logger.info(f"Delete channel started, {len(channels)} channels available")
        
    except Exception as e:
        logger.error(f"Failed to start delete channel: {e}")
        await message.answer("❌ Kanallar ro'yxatini olib bo'lmadi")


@dp.callback_query(F.data == "back_admin", DelChannelState.delete_channel)
async def back_to_admin(call: CallbackQuery, state: FSMContext) -> None:
    """Admin menyuga qaytish"""
    await call.message.delete()
    await state.clear()
    await call.message.answer("🔐 Admin menyu", reply_markup=admin_keyboard.admin_button)
    await call.answer()


@dp.callback_query(DelChannelState.delete_channel)
async def delete_channel(call: CallbackQuery, state: FSMContext) -> None:
    """Kanalni o'chirish"""
    await call.message.delete()
    
    try:
        chat = await bot.get_chat(call.data)
        channel_id = chat.id
        
        db.delete_channel(channel_id)
        
        text = (
            f"✅ Kanal o'chirildi!\n\n"
            f"📛 Nomi: <b>{chat.title or chat.full_name}</b>"
        )
        
        await call.message.answer(text, parse_mode="HTML")
        logger.info(f"Channel deleted: {channel_id}")
        
    except Exception as err:
        logger.error(f"Failed to delete channel: {err}")
        await call.message.answer(f"❌ Xato: {err}")
    
    await state.clear()
    await call.message.answer("🔐 Admin menyu", reply_markup=admin_keyboard.admin_button)
    await call.answer()


@dp.message(F.text == "📈 Murojaatlar statistikasi", IsBotAdminFilter(ADMINS))
async def appeal_statistics(message: Message) -> None:
    """Murojaatlar statistikasini ko'rsatish"""
    stats = db.get_appeal_statistics()
    categories = db.get_category_statistics()
    risks = db.get_risk_statistics()

    category_lines = "\n".join([f"• {name}: {count}" for name, count in categories[:5]]) or "• Ma'lumot yo'q"
    risk_lines = "\n".join([f"• {name}: {count}" for name, count in risks]) or "• Ma'lumot yo'q"

    text = (
        "📈 <b>Murojaatlar statistikasi</b>\n\n"
        f"Jami: <b>{stats['total']}</b>\n"
        f"Bugun: <b>{stats['today']}</b>\n"
        f"Yuqori xavf: <b>{stats['high_risk']}</b>\n"
        f"Ko'rib chiqilmoqda: <b>{stats['in_review']}</b>\n"
        f"Yakunlangan: <b>{stats['resolved']}</b>\n\n"
        f"<b>Top toifalar</b>\n{category_lines}\n\n"
        f"<b>Xavf kesimi</b>\n{risk_lines}"
    )
    await message.answer(text, parse_mode="HTML")


@dp.message(F.text == "🆕 So'nggi murojaatlar", IsBotAdminFilter(ADMINS))
async def recent_appeals(message: Message) -> None:
    """So'nggi murojaatlarni ko'rsatish"""
    appeals = db.get_recent_appeals(limit=7)
    if not appeals:
        await message.answer("Hali murojaatlar mavjud emas.")
        return

    lines = ["🆕 <b>So'nggi murojaatlar</b>\n"]
    for appeal_id, _, full_name, phone, organization, category, risk_level, priority, status, created_at, message_text, is_anonymous in appeals:
        organization_name = organization or "ko'rsatilmagan"
        mode = "Anonim" if is_anonymous else "Oddiy"
        display_name = "Anonim yuboruvchi" if is_anonymous else full_name
        display_phone = "Yashirilgan" if is_anonymous else phone
        preview = (message_text or "").strip().replace("\n", " ")
        if len(preview) > 220:
            preview = f"{preview[:217]}..."
        lines.append(
            f"#{appeal_id} | {display_name} | {category} | {risk_level} | {status}\n"
            f"Tel: {display_phone} | Bo'lim: {organization_name} | Rejim: {mode}\n"
            f"Muhimlik: {priority} | Sana: {created_at}\n"
            f"Murojaat: {preview}\n"
        )
    await message.answer("\n".join(lines), parse_mode="HTML")


@dp.message(F.text == "📄 PDF hisobot", IsBotAdminFilter(ADMINS))
async def export_pdf_report(message: Message) -> None:
    """PDF hisobot yaratish va yuborish"""
    stats = db.get_appeal_statistics()
    recent = db.get_recent_appeals(limit=10)
    categories = db.get_category_statistics()
    risks = db.get_risk_statistics()

    reports_dir = os.path.join(os.getcwd(), "reports")
    output_path = os.path.join(reports_dir, "appeals_report.pdf")
    generate_statistics_pdf(
        output_path=output_path,
        stats=stats,
        category_stats=categories,
        risk_stats=risks,
        recent_appeals=recent,
    )

    await message.answer_document(
        document=FSInputFile(output_path),
        caption="Korrupsiyaga oid murojaatlar bo'yicha PDF hisobot",
    )
