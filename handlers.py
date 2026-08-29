from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from keyboards import main_menu, get_subscription_keyboard, get_movie_keyboard
import database as db
import random as rand_module

router = Router()

async def check_user_subscription(bot: Bot, user_id: int) -> tuple[bool, list]:
    channels = db.get_channels()
    if not channels:
        return True, []
    unsubscribed = []
    for ch_id, ch_url, title in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch_id, user_id=user_id)
            if member.status in ["left", "kicked"]:
                unsubscribed.append((ch_id, ch_url, title))
        except Exception:
            pass
    return len(unsubscribed) == 0, unsubscribed

async def send_movie_to_user(bot: Bot, user_id: int, movie: tuple) -> bool:
    m_id = movie[0]
    code = movie[1]
    title = movie[2]
    file_id = movie[3]
    desc = movie[4]
    views = movie[5]
    msg_id = movie[6] if len(movie) > 6 else 0

    caption = f"🎬 <b>{title}</b>\n\n🔢 Kodi: <code>{code}</code>\n👁️ Ko'rishlar: {views + 1}\n\n🍿 <i>Maroqli tomosha tilaymiz!</i>\n🤖 @{(await bot.get_me()).username}"
    if desc:
        caption = f"🎬 <b>{title}</b>\n\n📝 {desc}\n\n🔢 Kodi: <code>{code}</code>\n👁️ Ko'rishlar: {views + 1}\n\n🍿 <i>Maroqli tomosha tilaymiz!</i>\n🤖 @{(await bot.get_me()).username}"

    db_channel = db.get_db_channel()
    if db_channel and msg_id and msg_id > 0:
        try:
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=int(db_channel),
                message_id=msg_id,
                caption=caption,
                reply_markup=get_movie_keyboard(code),
                protect_content=True,
                parse_mode="HTML"
            )
            return True
        except Exception:
            pass

    try:
        await bot.send_video(chat_id=user_id, video=file_id, caption=caption, reply_markup=get_movie_keyboard(code), protect_content=True, parse_mode="HTML")
        return True
    except Exception:
        try:
            await bot.send_document(chat_id=user_id, document=file_id, caption=caption, reply_markup=get_movie_keyboard(code), protect_content=True, parse_mode="HTML")
            return True
        except Exception:
            return False

@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    user = message.from_user
    db.add_user(user.id, user.full_name or "", user.username or "")

    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        movie_code = args[1].strip()
        is_sub, unsubs = await check_user_subscription(bot, user.id)
        if not is_sub:
            await message.answer("⚠️ <b>Kinoni ko'rish uchun quyidagi homiy kanallarga a'zo bo'ling:</b>", reply_markup=get_subscription_keyboard(unsubs), parse_mode="HTML")
            return
        movie = db.get_movie_by_code(movie_code)
        if movie:
            await send_movie_to_user(bot, user.id, movie)
            return

    await message.answer(
        f"Assalomu alaykum, <b>{user.full_name or 'Foydalanuvchi'}</b>!\n\n🎬 <b>Kino Botiga xush kelibsiz!</b>\n\nKino kodini yuboring yoki kino nomini yozing.\nMasalan: <code>101</code>",
        reply_markup=main_menu, parse_mode="HTML"
    )

@router.message(Command("latest"))
@router.message(F.text == "🎬 So'nggi kinolar")
async def show_latest_movies(message: Message):
    movies = db.get_latest_movies(10)
    if not movies:
        await message.answer("Hozircha bazada kinolar mavjud emas.")
        return
    text = "🎬 <b>Eng so'nggi kinolar:</b>\n\n"
    for idx, (code, title, views) in enumerate(movies, 1):
        text += f"{idx}. <b>{title}</b>\n👉 Kodi: <code>{code}</code> (👁️ {views} ko'rilgan)\n\n"
    text += "<i>Tomosha qilish uchun kodini botga yuboring!</i>"
    await message.answer(text, parse_mode="HTML")

@router.message(Command("random"))
@router.message(F.text == "🎲 Tasodifiy kino")
async def random_movie(message: Message, bot: Bot):
    movies = db.get_latest_movies(50)
    if not movies:
        await message.answer("Hozircha kinolar mavjud emas.")
        return
    chosen = rand_module.choice(movies)
    movie = db.get_movie_by_code(chosen[0])
    if movie:
        await send_movie_to_user(bot, message.from_user.id, movie)

@router.message(Command("search"))
@router.message(F.text == "🔍 Kino qidirish (Kod / Nom)")
async def search_hint(message: Message):
    await message.answer("Kino kodini (masalan: <code>101</code>) yoki nomini yozing:", parse_mode="HTML")

@router.message(Command("stats"))
@router.message(F.text == "📊 Statistika")
async def user_stats(message: Message):
    top_movies = db.get_top_movies(5)
    text = (
        f"📊 <b>Bot statistikasi:</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{db.get_users_count()}</b> ta\n"
        f"🎬 Kinolar: <b>{db.get_movies_count()}</b> ta\n"
        f"⚡ Holat: 24/7 Faol\n\n"
        f"🏆 <b>Eng ko'p ko'rilgan top 5 kino:</b>\n\n"
    )
    if top_movies:
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        for idx, (code, title, views) in enumerate(top_movies):
            text += f"{medals[idx]} <b>{title}</b>\n    📌 Kod: <code>{code}</code> | 👁️ {views} marta\n\n"
    else:
        text += "Hozircha ma'lumot yo'q.\n"
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "ℹ️ Bot haqida")
async def about_bot(message: Message):
    await message.answer("ℹ️ <b>Kino Boti:</b>\nBarcha yangi kinolar va seriallarni o'zbek tilida yuqori sifatda tomosha qiling!", parse_mode="HTML")

@router.message(Command("help"))
@router.message(F.text == "📞 Yordam")
async def support_contact(message: Message):
    await message.answer(
        "📞 <b>Yordam:</b>\n\n"
        "/start - Botni ishga tushirish\n"
        "/search - Kino qidirish\n"
        "/latest - So'nggi kinolar\n"
        "/random - Tasodifiy kino\n"
        "/stats - Statistika\n\n"
        "Kino kodini yuborsangiz, kino ko'rsatiladi.\n"
        "Muammo bo'lsa adminga yozing.",
        parse_mode="HTML"
    )

@router.callback_query(F.data == "check_subscription")
async def callback_check_sub(callback: CallbackQuery, bot: Bot):
    is_sub, unsubs = await check_user_subscription(bot, callback.from_user.id)
    if is_sub:
        await callback.message.delete()
        await callback.message.answer("✅ <b>Barcha kanallarga a'zo bo'ldingiz!</b>\nEndi kino kodini yozishingiz mumkin!", reply_markup=main_menu, parse_mode="HTML")
    else:
        await callback.answer("❌ Hali hamma kanallarga a'zo bo'lmadingiz!", show_alert=True)

@router.callback_query(F.data == "show_latest")
async def callback_show_latest(callback: CallbackQuery):
    movies = db.get_latest_movies(5)
    if not movies:
        await callback.answer("Kinolar topilmadi.")
        return
    text = "🎬 <b>Eng so'nggi kinolar:</b>\n\n"
    for idx, (code, title, views) in enumerate(movies, 1):
        text += f"{idx}. <b>{title}</b> (Kod: <code>{code}</code>)\n"
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

@router.message(F.text)
async def process_user_query(message: Message, bot: Bot):
    query = message.text.strip()
    is_sub, unsubs = await check_user_subscription(bot, message.from_user.id)
    if not is_sub:
        await message.answer("⚠️ <b>Kinoni ko'rish uchun quyidagi homiy kanallarga a'zo bo'ling:</b>", reply_markup=get_subscription_keyboard(unsubs), parse_mode="HTML")
        return

    movie = db.get_movie_by_code(query)
    if movie:
        await send_movie_to_user(bot, message.from_user.id, movie)
        return

    matches = db.search_movies_by_title(query)
    if matches:
        text = f"🔎 <b>'{query}' bo'yicha topilgan natijalar:</b>\n\n"
        for idx, (code, title) in enumerate(matches, 1):
            text += f"{idx}. <b>{title}</b>\n👉 Kodi: <code>{code}</code>\n\n"
        text += "<i>Tomosha qilish uchun kodini botga yuboring!</i>"
        await message.answer(text, parse_mode="HTML")
        return

    await message.answer(f"❌ <b>'{query}' topilmadi.</b>\n\nKodni to'g'ri kiritganingizni tekshiring.", reply_markup=main_menu, parse_mode="HTML")

