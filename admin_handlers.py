import os
import math
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from keyboards import (
    admin_menu, 
    main_menu, 
    cancel_keyboard, 
    get_admin_movies_pagination_keyboard,
    get_admins_management_keyboard
)
import database as db
import config

admin_router = Router()

class AdminStates(StatesGroup):
    waiting_for_video = State()
    waiting_for_code = State()
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_delete_code = State()
    waiting_for_new_admin_id = State()
    waiting_for_broadcast = State()
    waiting_for_channel = State()
    waiting_for_channel_id = State()
    waiting_for_channel_url = State()
    waiting_for_channel_name = State()
    waiting_for_edit_code = State()
    waiting_for_edit_title = State()
    waiting_for_edit_desc = State()

@admin_router.message(Command("admin"))
async def admin_panel(message: Message):
    if not db.is_admin(message.from_user.id):
        await message.answer("❌ Sizda admin huquqi yo'q.")
        return
    users_count = db.get_users_count()
    movies_count = db.get_movies_count()
    baza_status = f"<code>{config.BAZA_ID}</code>" if config.BAZA_ID else "❌ .env da BAZA_ID belgilanmagan"
    await message.answer(
        f"👑 <b>Admin paneliga xush kelibsiz!</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{users_count}</b> ta\n"
        f"🎬 Kinolar: <b>{movies_count}</b> ta\n"
        f"📁 Baza guruhi: {baza_status}\n\n"
        f"Kerakli bo'limni tanlang:",
        reply_markup=admin_menu, parse_mode="HTML"
    )

# ----------------- KINO QO'SHISH -----------------
@admin_router.message(F.text == "➕ Yangi kino qo'shish")
async def add_movie_start(message: Message, state: FSMContext):
    if not db.is_admin(message.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_video)
    await message.answer("🎬 <b>Yangi kino qo'shish</b>\n\nVideo faylni yuboring (MP4, MKV, AVI):\n<i>Bekor qilish uchun pastdagi tugmani bosing.</i>", reply_markup=cancel_keyboard, parse_mode="HTML")

@admin_router.message(AdminStates.waiting_for_video, F.text)
async def waiting_video_got_text(message: Message, state: FSMContext):
    """Admin video o'rniga matn yuborsa — bekor qilish yoki eslatma."""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu)
        return
    await message.answer("⚠️ Iltimos, <b>video fayl yuboring</b> yoki ❌ Bekor qilish bosing.", parse_mode="HTML")

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
    # Kinoni to'g'ridan-to'g'ri baza guruhiga yuborish (.env dagi BAZA_ID)
    if config.BAZA_ID:
        try:
            caption = f"🎬 <b>{data['title']}</b>\n\n🔢 Kodi: <code>{data['code']}</code>"
            if description:
                caption += f"\n\n📝 {description}"
            caption += f"\n\n#kino_{data['code']}"

            try:
                sent = await bot.send_video(chat_id=int(config.BAZA_ID), video=data["file_id"], caption=caption, parse_mode="HTML")
                msg_id = sent.message_id
            except Exception:
                sent = await bot.send_document(chat_id=int(config.BAZA_ID), document=data["file_id"], caption=caption, parse_mode="HTML")
                msg_id = sent.message_id
        except Exception as e:
            logging.error(f"Guruhga yuborishda xatolik: {e}")

    success = db.add_movie(data["code"], data["title"], data["file_id"], description, msg_id)
    await state.clear()
    if success:
        bot_info = await message.bot.get_me()
        deep_link = f"https://t.me/{bot_info.username}?start={data['code']}"
        baza_note = "\n📁 <i>Kino baza guruhiga ham saqlandi!</i>" if msg_id > 0 else "\n⚠️ <i>Baza guruhiga yuborilmadi (BAZA_ID sozlanmagan)</i>"
        await message.answer(
            f"✅ <b>Kino muvaffaqiyatli qo'shildi!</b>\n\n"
            f"🎬 Nom: <b>{data['title']}</b>\n"
            f"🔢 Kod: <code>{data['code']}</code>\n"
            f"🔗 Havola: {deep_link}{baza_note}",
            reply_markup=admin_menu, parse_mode="HTML"
        )
    else:
        await message.answer(f"❌ <code>{data['code']}</code> kodi allaqachon mavjud!", reply_markup=admin_menu, parse_mode="HTML")

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
    try:
        await call.message.delete()
    except Exception:
        pass
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
        m_id, m_code, m_title, file_id, desc, views, msg_id = movie
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
    m_id, m_code, m_title, file_id, desc, views, msg_id = movie
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

# ----------------- ADMINLARNI BOSHQARISH -----------------
@admin_router.message(F.text == "👑 Adminlar")
async def admins_menu_show(message: Message):
    if not db.is_admin(message.from_user.id):
        return
    admins = db.get_admins_list()
    text = f"👑 <b>Adminlar ro'yxati (Jami: {len(admins)} ta):</b>\n\n"
    for idx, (u_id, name, uname, date) in enumerate(admins, 1):
        uname_text = f" (@{uname})" if uname else ""
        name_text = name or "Admin"
        text += f"{idx}. <b>{name_text}</b>{uname_text} — <code>{u_id}</code>\n"
    text += "\nYangi admin qo'shish yoki o'chirish uchun quyidagi tugmalardan foydalaning:"
    await message.answer(text, reply_markup=get_admins_management_keyboard(admins), parse_mode="HTML")

@admin_router.callback_query(F.data == "admin_add")
async def admin_add_start(call: CallbackQuery, state: FSMContext):
    if not db.is_admin(call.from_user.id):
        await call.answer("❌ Huquq yo'q", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_for_new_admin_id)
    await call.message.answer(
        "👑 <b>Yangi admin qo'shish</b>\n\n"
        "Yangi adminning <b>Telegram User ID</b> sini kiriting (masalan: <code>7909677265</code>):",
        reply_markup=cancel_keyboard,
        parse_mode="HTML"
    )
    await call.answer()

@admin_router.message(AdminStates.waiting_for_new_admin_id, F.text)
async def admin_add_finish(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu)
        return
    raw_id = message.text.strip()
    if not raw_id.isdigit():
        await message.answer("❌ Faqat sonli ID kiriting (masalan: <code>7909677265</code>):", parse_mode="HTML")
        return
    new_admin_id = int(raw_id)
    success = db.add_admin(new_admin_id, "Admin")
    await state.clear()
    if success:
        await message.answer(f"✅ <b>Foydalanuvchi (ID: <code>{new_admin_id}</code>) admin qilindi!</b>", reply_markup=admin_menu, parse_mode="HTML")
    else:
        await message.answer("❌ Admin qo'shishda xatolik yuz berdi.", reply_markup=admin_menu)

@admin_router.callback_query(F.data == "admin_remove_menu")
async def admin_remove_menu(call: CallbackQuery):
    if not db.is_admin(call.from_user.id):
        await call.answer("❌ Huquq yo'q", show_alert=True)
        return
    admins = db.get_admins_list()
    if not admins:
        await call.answer("Adminlar topilmadi", show_alert=True)
        return
    buttons = []
    for u_id, name, uname, _ in admins:
        btn_text = f"🗑 {name or 'Admin'} ({u_id})"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"adm_remove_do:{u_id}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Ortga", callback_data="adm_close")])
    await call.message.edit_text("🗑 <b>O'chirmoqchi bo'lgan adminni tanlang:</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await call.answer()

@admin_router.callback_query(F.data.startswith("adm_remove_do:"))
async def on_admin_remove_do(call: CallbackQuery):
    if not db.is_admin(call.from_user.id):
        await call.answer("❌ Huquq yo'q", show_alert=True)
        return
    target_id = int(call.data.split(":")[1])
    if target_id == call.from_user.id:
        await call.answer("❌ O'zingizni o'chira olmaysiz!", show_alert=True)
        return
    db.remove_admin(target_id)
    await call.answer(f"✅ Admin ({target_id}) o'chirildi!", show_alert=True)
    try:
        await call.message.delete()
    except Exception:
        pass

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

# ----------------- HOMIY KANALLAR (INLINE UI) -----------------
def get_channels_keyboard(channels):
    """Kanallar inline keyboard"""
    btns = []
    for ch_id, ch_url, title in channels:
        btns.append([
            InlineKeyboardButton(text=f"🔗 {title}", url=ch_url),
            InlineKeyboardButton(text="🗑 O'chir", callback_data=f"ch_del:{ch_id}")
        ])
    btns.append([InlineKeyboardButton(text="➕ Yangi kanal qo'shish", callback_data="ch_add")])
    btns.append([InlineKeyboardButton(text="❌ Yopish", callback_data="adm_close")])
    return InlineKeyboardMarkup(inline_keyboard=btns)

@admin_router.message(F.text == "🔗 Homiy kanallar")
async def manage_channels(message: Message, state: FSMContext):
    if not db.is_admin(message.from_user.id):
        return
    await state.clear()
    channels = config.get_channels()
    text = "🔗 <b>Homiy kanallar:</b>\n"
    text += f"<i>Jami: {len(channels)} ta kanal</i>\n\n"
    if channels:
        for i, (ch_id, ch_url, title) in enumerate(channels, 1):
            text += f"{i}. <b>{title}</b> | <code>{ch_id}</code>\n"
    else:
        text += "Hozircha kanal yo'q.\n"
    text += "\n<i>Kanal qo'shish yoki o'chirish uchun tugmalardan foydalaning:</i>"
    await message.answer(text, reply_markup=get_channels_keyboard(channels), parse_mode="HTML")

@admin_router.callback_query(F.data == "ch_add")
async def channel_add_start(call: CallbackQuery, state: FSMContext):
    if not db.is_admin(call.from_user.id):
        await call.answer()
        return
    await state.set_state(AdminStates.waiting_for_channel_id)
    await call.message.answer(
        "➕ <b>Yangi kanal qo'shish</b>\n\n"
        "1-qadam: Kanal/guruh <b>username</b> yoki <b>ID</b> sini yuboring:\n"
        "Masalan: <code>@kanal_nomi</code> yoki <code>-1001234567890</code>",
        reply_markup=cancel_keyboard, parse_mode="HTML"
    )
    await call.answer()

@admin_router.message(AdminStates.waiting_for_channel_id, F.text)
async def channel_add_got_id(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu)
        return
    await state.update_data(ch_id=message.text.strip())
    await state.set_state(AdminStates.waiting_for_channel_url)
    await message.answer(
        "2-qadam: Kanal <b>havolasini</b> yuboring:\n"
        "Masalan: <code>https://t.me/kanal_nomi</code>",
        parse_mode="HTML"
    )

@admin_router.message(AdminStates.waiting_for_channel_url, F.text)
async def channel_add_got_url(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu)
        return
    await state.update_data(ch_url=message.text.strip())
    await state.set_state(AdminStates.waiting_for_channel_name)
    await message.answer(
        "3-qadam: Kanal <b>nomini</b> yuboring:\n"
        "Masalan: <code>KINO comfy</code>",
        parse_mode="HTML"
    )

@admin_router.message(AdminStates.waiting_for_channel_name, F.text)
async def channel_add_got_name(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu)
        return
    data = await state.get_data()
    title = message.text.strip()
    config.add_channel(data["ch_id"], data["ch_url"], title)
    await state.clear()
    channels = config.get_channels()
    await message.answer(
        f"✅ <b>{title}</b> kanali qo'shildi!\n💾 <i>.env ga saqlandi</i>",
        reply_markup=admin_menu, parse_mode="HTML"
    )
    await message.answer(
        "🔗 <b>Yangilangan kanallar:</b>",
        reply_markup=get_channels_keyboard(channels), parse_mode="HTML"
    )

@admin_router.callback_query(F.data.startswith("ch_del:"))
async def channel_delete(call: CallbackQuery):
    if not db.is_admin(call.from_user.id):
        await call.answer()
        return
    ch_id = call.data.split(":", 1)[1]
    config.delete_channel(ch_id)
    channels = config.get_channels()
    await call.answer(f"✅ {ch_id} o'chirildi!", show_alert=True)
    text = "🔗 <b>Homiy kanallar:</b>\n"
    text += f"<i>Jami: {len(channels)} ta kanal</i>\n\n"
    for i, (cid, curl, ctitle) in enumerate(channels, 1):
        text += f"{i}. <b>{ctitle}</b> | <code>{cid}</code>\n"
    if not channels:
        text += "Hozircha kanal yo'q.\n"
    try:
        await call.message.edit_text(text, reply_markup=get_channels_keyboard(channels), parse_mode="HTML")
    except Exception:
        pass

# ----------------- KINO TAHRIRLASH -----------------
@admin_router.message(F.text == "✏️ Kinoni tahrirlash")
async def edit_movie_start(message: Message, state: FSMContext):
    if not db.is_admin(message.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_edit_code)
    await message.answer(
        "✏️ <b>Kinoni tahrirlash</b>\n\nTahrirlamoqchi bo'lgan kinoning <b>kodini</b> kiriting:",
        reply_markup=cancel_keyboard, parse_mode="HTML"
    )

@admin_router.message(AdminStates.waiting_for_edit_code, F.text)
async def edit_movie_got_code(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu)
        return
    code = message.text.strip()
    movie = db.get_movie_by_code(code)
    if not movie:
        await message.answer(f"❌ <code>{code}</code> kodli kino topilmadi. Qayta kiriting:", parse_mode="HTML")
        return
    await state.update_data(edit_code=code, old_title=movie[2], old_desc=movie[4])
    edit_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎥 Nomini o'zgartirish", callback_data="edit_title")],
        [InlineKeyboardButton(text="📝 Tavsifini o'zgartirish", callback_data="edit_desc")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="edit_cancel")]
    ])
    await message.answer(
        f"🎬 <b>{movie[2]}</b>\n"
        f"Kod: <code>{code}</code>\n"
        f"Tavsif: {movie[4] or '<i>yo\'q</i>'}\n\n"
        f"Nimani o'zgartirmoqchisiz?",
        reply_markup=edit_kb, parse_mode="HTML"
    )

@admin_router.callback_query(F.data == "edit_title")
async def edit_title_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_edit_title)
    data = await state.get_data()
    await call.message.answer(
        f"Hozirgi nom: <b>{data.get('old_title', '')}</b>\n\nYangi nomni kiriting:",
        reply_markup=cancel_keyboard, parse_mode="HTML"
    )
    await call.answer()

@admin_router.callback_query(F.data == "edit_desc")
async def edit_desc_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_edit_desc)
    data = await state.get_data()
    await call.message.answer(
        f"Hozirgi tavsif: <i>{data.get('old_desc') or 'yo\'q'}</i>\n\nYangi tavsifni kiriting (yoki <code>-</code> o'chirish uchun):",
        reply_markup=cancel_keyboard, parse_mode="HTML"
    )
    await call.answer()

@admin_router.callback_query(F.data == "edit_cancel")
async def edit_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.answer("❌ Bekor qilindi.", reply_markup=admin_menu)
    await call.answer()

@admin_router.message(AdminStates.waiting_for_edit_title, F.text)
async def edit_title_finish(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu)
        return
    data = await state.get_data()
    code = data.get("edit_code")
    new_title = message.text.strip()
    db.update_movie(code, new_title=new_title)
    await state.clear()
    await message.answer(
        f"✅ <b>{code}</b> kino nomi yangilandi!\n"
        f"Yangi nom: <b>{new_title}</b>",
        reply_markup=admin_menu, parse_mode="HTML"
    )

@admin_router.message(AdminStates.waiting_for_edit_desc, F.text)
async def edit_desc_finish(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu)
        return
    data = await state.get_data()
    code = data.get("edit_code")
    new_desc = "" if message.text.strip() == "-" else message.text.strip()
    db.update_movie(code, new_description=new_desc)
    await state.clear()
    await message.answer(
        f"✅ <b>{code}</b> kino tavsifi yangilandi!",
        reply_markup=admin_menu, parse_mode="HTML"
    )

# ----------------- MENYUGA QAYTISH -----------------
@admin_router.message(F.text == "⬅️ Foydalanuvchi menyusi")
async def back_to_user_menu(message: Message):
    await message.answer("Foydalanuvchi menyusi:", reply_markup=main_menu)
