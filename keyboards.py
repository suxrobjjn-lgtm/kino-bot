from aiogram.types import (
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton
)

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔍 Kino qidirish (Kod / Nom)"), KeyboardButton(text="🎬 So'nggi kinolar")],
        [KeyboardButton(text="🎲 Tasodifiy kino"), KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="ℹ️ Bot haqida"), KeyboardButton(text="📞 Yordam")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Kino kodini yoki nomini yozing..."
)

cancel_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
    resize_keyboard=True
)

admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Yangi kino qo'shish"), KeyboardButton(text="📋 Barcha kinolar")],
        [KeyboardButton(text="🗑 Kinoni o'chirish"), KeyboardButton(text="📊 To'liq statistika")],
        [KeyboardButton(text="📢 Xabar tarqatish (Reklama)"), KeyboardButton(text="🔗 Homiy kanallar")],
        [KeyboardButton(text="⬅️ Foydalanuvchi menyusi")]
    ],
    resize_keyboard=True
)

def get_admin_movies_pagination_keyboard(page: int, total_pages: int, movies: list):
    inline_keyboard = []
    
    # Har bir kino uchun o'chirish tugmasi (qatoriga 2 tadan)
    row = []
    for id_, code, title, views, _ in movies:
        btn_text = f"🗑 {code}"
        row.append(InlineKeyboardButton(text=btn_text, callback_data=f"adm_del_confirm:{code}"))
        if len(row) == 2:
            inline_keyboard.append(row)
            row = []
    if row:
        inline_keyboard.append(row)
        
    # Sahifalash tugmalari (Pagination)
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"adm_page:{page - 1}"))
    nav_row.append(InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"adm_page:{page + 1}"))
    
    inline_keyboard.append(nav_row)
    inline_keyboard.append([InlineKeyboardButton(text="❌ Yopish", callback_data="adm_close")])
    
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

def get_subscription_keyboard(channels: list):
    inline_keyboard = []
    for idx, (ch_id, ch_url, title) in enumerate(channels, 1):
        inline_keyboard.append([InlineKeyboardButton(text=f"👉 {idx}-kanal: {title}", url=ch_url)])
    inline_keyboard.append([InlineKeyboardButton(text="✅ Obunani tekshirish 🔄", callback_data="check_subscription")])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

def get_movie_keyboard(movie_code: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🎬 Boshqa kinolar", callback_data="show_latest")]]
    )

