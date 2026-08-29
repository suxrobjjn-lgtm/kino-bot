import os
import math
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from keyboards import admin_menu, main_menu, cancel_keyboard, get_admin_movies_pagination_keyboard
import database as db

admin_router = Router()

class AdminStates(StatesGroup):
    waiting_for_video = State()
    waiting_for_code = State()
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_delete_code = State()
    waiting_for_broadcast = State()
    waiting_for_channel = State()

def admin_required(func):
    async def wrapper(message: Message, *args, **kwargs):
        if not db.is_admin(message.from_user.id):
            await message.answer("❌ Sizda admin huquqi yo'q.")
            return
        return await func(message, *args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

@admin_router.message(Command("admin"))
async def admin_panel(message: Message):
    if not db.is_admin(message.from_user.id):
        await message.answer("❌ Sizda admin huquqi yo'q.")
        return
    users_count = db.get_users_count()
    movies_count = db.get_movies_count()
    await message.answer(
        f"👑 <b>Admin paneliga xush kelibsiz!</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{users_count}</b> ta\n"
        f"🎬 Kinolar: <b>{movies_count}</b> ta\n\n"
        f"Quyidagi tugmalardan birini tanlang:",
        reply_markup=admin_menu, parse_mode="HTML"
    )

# ----------------- KINO QO'SHISH -----------------
@admin_router.message(F.text == "➕ Yangi kino qo'shish")
async def add_movie_start(message: Message, state: FSMContext):
    if not db.is_admin(message.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_video)
    await message.answer("🎬 <b>Yangi kino qo'shish</b>\n\nVideo faylni yuboring (MP4, MKV, AVI):", reply_markup=cancel_keyboard, parse_mode="HTML")

@admin_router.message(AdminStates.waiting_for_video, F.video | F.document)
async def receive_video(message: Message, state: FSMContext):
    if message.video:
        file_id = message.video.file_id
    elif message.document:
        file_id = message.document.file_id
    else:
        await message.answer("Iltimos video fayl yuboring.")
        return
    await state.update_data(file_id=file_id)
    await state.set_state(AdminStates.waiting_for_code)
    await message.answer("✅ Video qabul qilindi!\n\n<b>Kino kodini kiriting</b> (masalan: <code>101</code>):", parse_mode="HTML")

@admin_router.message(AdminStates.waiting_for_code, F.text)
async def receive_code(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu)
        return
    code = message.text.strip()
    await state.update_data(code=code)
    await state.set_state(AdminStates.waiting_for_title)
    await message.answer(f"✅ Kod: <code>{code}</code>\n\n<b>Kino nomini kiriting:</b>", parse_mode="HTML")

@admin_router.message(AdminStates.waiting_for_title, F.text)
async def receive_title(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu)
        return
    title = message.text.strip()
    await state.update_data(title=title)
    await state.set_state(AdminStates.waiting_for_description)
    await message.answer(f"✅ Nom: <b>{title}</b>\n\n<b>Tavsif kiriting</b> (yoki 'O'tkazib yuborish' deb yozing):", parse_mode="HTML")

@admin_router.message(AdminStates.waiting_for_description, F.text)
async def receive_description(message: Message, state: FSMContext, bot: Bot):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu)
        return
    description = "" if message.text.strip().lower() in ["o'tkazib yuborish", "skip", "-"] else message.text.strip()
    data = await state.get_data()

    msg_id = 0
    db_channel = db.get_db_channel()
    if db_channel:
        try:
            caption = f"🎬 <b>{data['title']}</b>\n\n🔢 Kodi: <code>{data['code']}</code>"
            if description:
                caption += f"\n\n📝 {description}"
            caption += f"\n\n#kino_{data['code']}"

            try:
                sent = await bot.send_video(chat_id=int(db_channel), video=data["file_id"], caption=caption, parse_mode="HTML")
                msg_id = sent.message_id
            except Exception:
                sent = await bot.send_document(chat_id=int(db_channel), document=data["file_id"], caption=caption, parse_mode="HTML")
                msg_id = sent.message_id
        except Exception as e:
            pass

    success = db.add_movie(data["code"], data["title"], data["file_id"], description, msg_id)
    await state.clear()
    if success:
        bot_info = await message.bot.get_me()
        deep_link = f"https://t.me/{bot_info.username}?start={data['code']}"
        await message.answer(
            f"✅ <b>Kino muvaffaqiyatli qo'shildi!</b>\n\n"
            f"🎬 Nom: <b>{data['title']}</b>\n"
            f"🔢 Kod: <code>{data['code']}</code>\n"
            f"🔗 Havola: {deep_link}",
            reply_markup=admin_menu, parse_mode="HTML"
        )
    else:
        await message.answer(f"❌ <code>{data['code']}</code> kodi allaqachon mavjud!", reply_markup=admin_menu, parse_mode="HTML")

# ----------------- BAZA GURUHINI ULASH -----------------
@admin_router.message(F.chat.type.in_(["group", "supergroup", "channel"]), Command("set_baza", "id", "connect", "baza", "start"))
@admin_router.channel_post(Command("set_baza", "id", "connect", "baza", "start"))
async def set_baza_directly_in_chat(message: Message):
    chat_id = message.chat.id
    chat_title = message.chat.title or "Baza guruhi"
    db.set_db_channel(chat_id)
    await message.reply(
        f"✅ <b>Baza guruhi/kanali muvaffaqiyatli ulandi!</b> 🎉\n\n"
        f"🏷 Nomi: <b>{chat_title}</b>\n"
        f"🆔 ID: <code>{chat_id}</code>\n\n"
        f"Endi botga qo'shilgan barcha kinolar avtomatik shu yerga saqlanadi!",
        parse_mode="HTML"
    )

@admin_router.message(Command("set_baza"))
async def cmd_set_baza(message: Message):
    if not db.is_admin(message.from_user.id):
        return
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        ch_id = args[1].strip()
        db.set_db_channel(ch_id)
        await message.answer(f"✅ <b>Baza kanali ID si saqlandi:</b> <code>{ch_id}</code>", parse_mode="HTML")
    else:
        current = db.get_db_channel()
        await message.answer(
            f"📁 <b>Baza kanali sozlamasi:</b>\n\nHozirgi ID: <code>{current or 'Ulanmagan'}</code>\n\n"
            f"Ulash uchun:\n1. Ochgan guruhingiz ichiga kirib <code>/set_baza</code> deb yozing\n2. Yoki guruhdan bitta xabarni botga forward qiling\n3. Yoki <code>/set_baza -100xxxxxxx</code> deb yozing.",
            parse_mode="HTML"
        )

@admin_router.message(F.forward_origin | F.forward_from_chat)
async def handle_forward_for_baza(message: Message):
    if not db.is_admin(message.from_user.id):
        return
    chat_id = None
    chat_title = "Baza guruhi/kanali"
    if message.forward_origin and hasattr(message.forward_origin, "chat"):
        chat_id = message.forward_origin.chat.id
        chat_title = getattr(message.forward_origin.chat, "title", "Baza guruhi")
    elif message.forward_from_chat:
        chat_id = message.forward_from_chat.id
        chat_title = message.forward_from_chat.title

    if chat_id:
        db.set_db_channel(chat_id)
        await message.answer(
            f"✅ <b>Baza guruhi/kanali muvaffaqiyatli ulandi!</b> 🎉\n\n"
            f"🏷 Nomi: <b>{chat_title}</b>\n"
            f"🆔 ID: <code>{chat_id}</code>\n\n"
            f"Endi botga qo'shilgan har bir kino avtomatik tarzda ushbu guruhga tashlanadi va u yerdan hech qachon o'chib ketmaydi!",
            reply_markup=admin_menu,
            parse_mode="HTML"
        )



# ----------------- BARCHA KINOLAR RO'YXATI & PAGINATION -----------------
async def render_movies_page(page: int = 1, per_page: int = 8):
    movies, total_count = db.get_all_movies_list(page=page, per_page=per_page)
    if total_count == 0:
        return "🎬 <b>Hozircha bazada birorta ham kino mavjud emas.</b>", None
    
    total_pages = max(1, math.ceil(total_count / per_page))
    page = min(max(1, page), total_pages)
    
    text = f"📋 <b>Barcha kinolar ro'yxati</b> (Jami: <b>{total_count}</b> ta)\n"
    text += f"📄 Sahifa: <b>{page}/{total_pages}</b>\n\n"
    
    for idx, (id_, code, title, views, added_date) in enumerate(movies, (page - 1) * per_page + 1):
        text += f"<b>{idx}. {title}</b>\n"
        text += f"   👉 Kodi: <code>{code}</code> | 👁️ Ko'rishlar: {views}\n\n"
        
    text += "<i>💡 Kinoni o'chirish uchun pastdagi kerakli kino kodi tugmasini bosing:</i>"
    keyboard = get_admin_movies_pagination_keyboard(page, total_pages, movies)
    return text, keyboard

@admin_router.message(F.text == "📋 Barcha kinolar")
async def show_all_movies_admin(message: Message):
    if not db.is_admin(message.from_user.id):
        return
    text, keyboard = await render_movies_page(page=1)
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("adm_page:"))
async def on_movies_page_nav(call: CallbackQuery):
    if not db.is_admin(call.from_user.id):
        await call.answer("❌ Huquq yo'q", show_alert=True)
        return
    page = int(call.data.split(":")[1])
    text, keyboard = await render_movies_page(page=page)
    try:
        await call.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        pass
    await call.answer()

@admin_router.callback_query(F.data == "noop")
async def on_noop(call: CallbackQuery):
    await call.answer()

@admin_router.callback_query(F.data == "adm_close")
async def on_admin_close(call: CallbackQuery):
    await call.message.delete()
    await call.answer()

# ----------------- KINONI O'CHIRISH -----------------
@admin_router.message(F.text == "🗑 Kinoni o'chirish")
async def delete_movie_start(message: Message, state: FSMContext):
    if not db.is_admin(message.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_delete_code)
    await message.answer(
        "🗑 <b>Kinoni o'chirish</b>\n\n"
        "O'chirmoqchi bo'lgan kino kodini yozib yuboring (masalan: <code>101</code>):",
        reply_markup=cancel_keyboard,
        parse_mode="HTML"
    )

@admin_router.message(AdminStates.waiting_for_delete_code, F.text)
async def delete_movie_finish(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu)
        return
    code = message.text.strip()
    movie = db.get_movie_by_code(code)
    if not movie:
        await message.answer(f"❌ <code>{code}</code> kodli kino topilmadi. Qayta urinib ko'ring yoki Bekor qiling.", parse_mode="HTML")
        return
    
    deleted = db.delete_movie_by_code(code)
    await state.clear()
    if deleted:
        m_id, m_code, m_title, file_id, desc, views = movie
        await message.answer(
            f"✅ <b>Kino muvaffaqiyatli o'chirildi!</b>\n\n"
            f"🎬 Nom: <b>{m_title}</b>\n"
            f"🔢 Kod: <code>{m_code}</code>",
            reply_markup=admin_menu,
            parse_mode="HTML"
        )
    else:
        await message.answer("❌ O'chirishda xatolik yuz berdi.", reply_markup=admin_menu)

@admin_router.callback_query(F.data.startswith("adm_del_confirm:"))
async def on_del_confirm(call: CallbackQuery):
    if not db.is_admin(call.from_user.id):
        await call.answer("❌ Huquq yo'q", show_alert=True)
        return
    code = call.data.split(":", 1)[1]
    movie = db.get_movie_by_code(code)
    if not movie:
        await call.answer("❌ Kino topilmadi", show_alert=True)
        return
    m_id, m_code, m_title, file_id, desc, views = movie
    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha, o'chirilsin", callback_data=f"adm_del_do:{code}"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="adm_page:1")
        ]
    ])
    await call.message.edit_text(
        f"⚠️ <b>Haqiqatan ham ushbu kinoni o'chirmoqchimisiz?</b>\n\n"
        f"🎬 Nom: <b>{m_title}</b>\n"
        f"🔢 Kod: <code>{m_code}</code>",
        reply_markup=confirm_kb,
        parse_mode="HTML"
    )
    await call.answer()

@admin_router.callback_query(F.data.startswith("adm_del_do:"))
async def on_del_do(call: CallbackQuery):
    if not db.is_admin(call.from_user.id):
        await call.answer("❌ Huquq yo'q", show_alert=True)
        return
    code = call.data.split(":", 1)[1]
    deleted = db.delete_movie_by_code(code)
    if deleted:
        await call.answer(f"✅ {code} kodli kino o'chirildi!", show_alert=True)
    else:
        await call.answer("❌ Xatolik yuz berdi", show_alert=True)
    text, keyboard = await render_movies_page(page=1)
    await call.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

# ----------------- STATISTIKA -----------------
@admin_router.message(F.text == "📊 To'liq statistika")
async def full_statistics(message: Message):
    if not db.is_admin(message.from_user.id):
        return
    users = db.get_users_count()
    movies = db.get_movies_count()
    latest = db.get_latest_movies(5)
    text = f"📊 <b>To'liq statistika:</b>\n\n👥 Foydalanuvchilar: <b>{users}</b>\n🎬 Kinolar: <b>{movies}</b>\n\n🎯 <b>Eng so'nggi kinolar:</b>\n"
    for code, title, views in latest:
        text += f"• <b>{title}</b> (Kod: <code>{code}</code>) - 👁️ {views}\n"
    await message.answer(text, parse_mode="HTML")

# ----------------- REKLAMA -----------------
@admin_router.message(F.text == "📢 Xabar tarqatish (Reklama)")
async def broadcast_start(message: Message, state: FSMContext):
    if not db.is_admin(message.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_broadcast)
    await message.answer("📢 <b>Reklama xabarini yuboring:</b>\n(matn, rasm yoki video bo'lishi mumkin)", reply_markup=cancel_keyboard, parse_mode="HTML")

@admin_router.message(AdminStates.waiting_for_broadcast)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu)
        return
    await state.clear()
    users = db.get_all_users()
    success = 0
    fail = 0
    status_msg = await message.answer(f"📢 Xabar yuborilmoqda... (0/{len(users)})")
    for i, user_id in enumerate(users):
        try:
            await message.copy_to(user_id)
            success += 1
        except Exception:
            fail += 1
        if (i + 1) % 50 == 0:
            try:
                await status_msg.edit_text(f"📢 Xabar yuborilmoqda... ({i+1}/{len(users)})")
            except Exception:
                pass
    await status_msg.edit_text(f"✅ <b>Reklama yakunlandi!</b>\n\n✅ Muvaffaqiyatli: <b>{success}</b>\n❌ Xatolik: <b>{fail}</b>\n👥 Jami: <b>{len(users)}</b>", parse_mode="HTML")
    await message.answer("Admin panel:", reply_markup=admin_menu)

# ----------------- HOMIY KANALLAR -----------------
@admin_router.message(F.text == "🔗 Homiy kanallar")
async def manage_channels(message: Message, state: FSMContext):
    if not db.is_admin(message.from_user.id):
        return
    channels = db.get_channels()
    text = "🔗 <b>Homiy kanallar:</b>\n\n"
    if channels:
        for ch_id, ch_url, title in channels:
            text += f"• <b>{title}</b> | {ch_url} | ID: <code>{ch_id}</code>\n"
    else:
        text += "Hozircha kanal yo'q.\n"
    text += "\n<b>Kanal qo'shish:</b> <code>+ @kanal_username https://t.me/kanal Kanal nomi</code>\n<b>Kanal o'chirish:</b> <code>- @kanal_username</code>"
    await state.set_state(AdminStates.waiting_for_channel)
    await message.answer(text, reply_markup=cancel_keyboard, parse_mode="HTML")

@admin_router.message(AdminStates.waiting_for_channel, F.text)
async def process_channel_command(message: Message, state: FSMContext):
    text = message.text.strip()
    if text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu)
        return
    if text.startswith("+ "):
        parts = text[2:].split(maxsplit=2)
        if len(parts) >= 3:
            ch_id, ch_url, title = parts[0], parts[1], parts[2]
            db.add_channel(ch_id, ch_url, title)
            await message.answer(f"✅ <b>{title}</b> kanali qo'shildi!", reply_markup=admin_menu, parse_mode="HTML")
        else:
            await message.answer("❌ Format xato! <code>+ @kanal https://t.me/kanal Kanal nomi</code>", parse_mode="HTML")
    elif text.startswith("- "):
        ch_id = text[2:].strip()
        db.delete_channel(ch_id)
        await message.answer(f"✅ <code>{ch_id}</code> kanali o'chirildi!", reply_markup=admin_menu, parse_mode="HTML")
    else:
        await message.answer("Format xato! + yoki - bilan boshlang.", reply_markup=admin_menu)
    await state.clear()

# ----------------- MENYUGA QAYTISH -----------------
@admin_router.message(F.text == "⬅️ Foydalanuvchi menyusi")
async def back_to_user_menu(message: Message):
    await message.answer("Foydalanuvchi menyusi:", reply_markup=main_menu)
