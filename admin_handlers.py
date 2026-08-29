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
    get_baza_keyboard,
    get_admins_management_keyboard
)
import database as db

admin_router = Router()

class AdminStates(StatesGroup):
    waiting_for_video = State()
    waiting_for_code = State()
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_delete_code = State()
    waiting_for_baza_id = State()
    waiting_for_new_admin_id = State()
    waiting_for_broadcast = State()
    waiting_for_channel = State()

@admin_router.message(Command("admin"))
async def admin_panel(message: Message):
    if not db.is_admin(message.from_user.id):
        await message.answer("❌ Sizda admin huquqi yo'q.")
        return
    users_count = db.get_users_count()
    movies_count = db.get_movies_count()
    baza_id = db.get_db_channel()
    baza_status = f"<code>{baza_id}</code>" if baza_id else "❌ Ulanmagan"
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
            logging.error(f"Guruhga yuborishda xatolik: {e}")

    success = db.add_movie(data["code"], data["title"], data["file_id"], description, msg_id)
    await state.clear()
    if success:
        bot_info = await message.bot.get_me()
        deep_link = f"https://t.me/{bot_info.username}?start={data['code']}"
        baza_note = "\n📁 <i>Kino baza guruhiga ham saqlandi!</i>" if msg_id > 0 else ""
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

# ----------------- BAZA GURUHI SOZLAMALARI -----------------
@admin_router.message(F.text == "📁 Baza guruhi")
async def baza_menu_show(message: Message):
    if not db.is_admin(message.from_user.id):
        return
    baza_id = db.get_db_channel()
    status_text = f"✅ Ulanmagan: <code>{baza_id}</code>" if baza_id else "❌ Baza guruhi ulanmagan"
    text = (
        f"📁 <b>Baza guruhi sozlamalari:</b>\n\n"
        f"Holat: {status_text}\n\n"
        f"<i>💡 Baza guruhi ulanganda barcha yuklangan kinolar o'sha yerga avtomatik tashlanadi va hech qachon o'chib ketmaydi.</i>\n\n"
        f"Baza guruhini ulash uchun ID sini kiriting:"
    )
    await message.answer(text, reply_markup=get_baza_keyboard(bool(baza_id)), parse_mode="HTML")

@admin_router.callback_query(F.data == "baza_change")
async def baza_change_start(call: CallbackQuery, state: FSMContext):
    if not db.is_admin(call.from_user.id):
        await call.answer("❌ Huquq yo'q", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_for_baza_id)
    await call.message.answer(
        "📁 <b>Baza guruhi yoki kanali ID sini kiriting:</b>\n\n"
        "Masalan: <code>-1002345678901</code>\n"
        "<i>(Bot o'sha guruhda Admin bo'lishi shart)</i>",
        reply_markup=cancel_keyboard,
        parse_mode="HTML"
    )
    await call.answer()

@admin_router.message(AdminStates.waiting_for_baza_id, F.text)
async def baza_change_finish(message: Message, state: FSMContext, bot: Bot):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=admin_menu)
        return
    raw_id = message.text.strip()
    try:
        chat_id = int(raw_id)
        # Test whether bot has access
        try:
            chat = await bot.get_chat(chat_id)
            title = chat.title or "Baza guruhi"
            db.set_db_channel(chat_id)
            await state.clear()
            await message.answer(
                f"✅ <b>Baza guruhi muvaffaqiyatli ulandi!</b> 🎉\n\n"
                f"🏷 Guruh: <b>{title}</b>\n"
                f"🆔 ID: <code>{chat_id}</code>\n\n"
                f"Endi botga qo'shilgan barcha kinolar avtomatik shu yerga saqlanadi!",
                reply_markup=admin_menu,
                parse_mode="HTML"
            )
        except Exception as e:
            # Save anyway and notify
            db.set_db_channel(chat_id)
            await state.clear()
            await message.answer(
                f"✅ <b>Baza guruhi ID si saqlandi:</b> <code>{chat_id}</code>\n\n"
                f"⚠️ <i>Eslatma: Bot o'sha guruhga Admin qilib qo'shilganiga ishonch hosil qiling.</i>",
                reply_markup=admin_menu,
                parse_mode="HTML"
            )
    except ValueError:
        await message.answer("❌ ID raqam bo'lishi kerak (masalan: <code>-1002345678901</code>). Qayta urinib ko'ring yoki Bekor qiling:", parse_mode="HTML")

@admin_router.callback_query(F.data == "baza_disconnect")
async def baza_disconnect(call: CallbackQuery):
    if not db.is_admin(call.from_user.id):
        await call.answer("❌ Huquq yo'q", show_alert=True)
        return
    db.clear_db_channel()
    await call.message.edit_text("✅ <b>Baza guruhi uzildi.</b>", parse_mode="HTML")
    await call.answer("Baza guruhi uzildi", show_alert=True)

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
        # Don't show self delete if only one
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
