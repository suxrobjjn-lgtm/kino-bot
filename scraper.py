import os
import sys
import re
import asyncio
from telethon import TelegramClient
from telethon.tl.types import MessageMediaDocument

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="ignore")

# --- SOZLAMALAR ---
API_ID = 14029116
API_HASH = "0914ce00953d5dc0197ce5b18f90661f"
SESSION_PATH = "C:/Users/A C E R/ai_agent/user_session"

SOURCE_BOT = "UZBKINOMANTV_BOT"
MY_BOT_USERNAME = "eski_kinalar_bot"
BAZA_CHAT_ID = -1004294509106
CHANNEL_USERNAME = "kino_comfy_gr"

import sqlite3
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kino_bot.db")

def clean_text_formatting(text: str) -> str:
    """Yulduzchalar va ortiqcha belgilarni tozalaydi."""
    text = text.replace("**", "").replace("__", "").replace("``", "")
    return text.strip()

def parse_movie_caption(raw_text: str, code: int):
    """
    Kino tavsifidan begona bot/kanallarni va boshqa botning yuklashlar sonini tozalab, 
    chiroyli nom va asl tavsifni ajratadi.
    """
    if not raw_text:
        return f"Kino #{code}", ""
    
    lines = [clean_text_formatting(line) for line in raw_text.splitlines() if line.strip()]
    
    title = ""
    clean_lines = []
    
    for line in lines:
        line_lower = line.lower()
        # Begona reklamalarni va begona botning yuklashlar sonini olib tashlaymiz
        if any(bad in line_lower for bad in [
            "bizning bot", "botimiz", "kanalimiz", "@uzbkinomantv_bot", 
            "@sarafilmuz", "t.me/", "yuklash:", "yuklashlar:", "yuklab olish:"
        ]):
            continue
        
        # Sarlavhani aniqlash
        if not title:
            cleaned = re.sub(r'^[🎬🎥📸📽️🍿\s]+', '', line).strip()
            if cleaned and not cleaned.startswith("---") and not cleaned.startswith("==="):
                title = cleaned
                continue
                
        clean_lines.append(line)
        
    if not title:
        title = f"Kino #{code}"
        
    description = "\n".join(clean_lines)
    return title, description

import yt_dlp

def download_short_trailer(title: str, code: int) -> str | None:
    """YouTube dan kinoning ovozli qisqa treyler videosini yuklab oladi."""
    trailer_filename = f"trailer_{code}.mp4"
    clean_title = re.sub(r'\(.*?\)|\[.*?\]', '', title)
    clean_title = re.sub(r'[^\w\s]', ' ', clean_title).strip()
    
    # Bir nechta qidiruv variantlari
    search_queries = [
        f"ytsearch1:{clean_title} trailer",
        f"ytsearch1:{clean_title} rasmiy treyler",
        f"ytsearch1:{clean_title} official trailer"
    ]
    
    ydl_opts = {
        'format': '18/22/b/best',
        'extractor_args': {'youtube': {'player_client': ['android', 'web', 'tv']}},
        'outtmpl': trailer_filename,
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
    }
    
    for query in search_queries:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(query, download=True)
                if os.path.exists(trailer_filename):
                    return trailer_filename
        except Exception:
            continue
            
    return None

async def process_movie(client: TelegramClient, code: int) -> bool:
    print(f"\n[{code}] @{SOURCE_BOT} dan so'ralmoqda...")
    sent_msg = await client.send_message(SOURCE_BOT, str(code))
    
    video_msg = None
    for _ in range(12):
        await asyncio.sleep(1)
        messages = await client.get_messages(SOURCE_BOT, limit=5)
        for m in messages:
            if m.id > sent_msg.id and (m.video or (m.media and isinstance(m.media, MessageMediaDocument))):
                video_msg = m
                break
        if video_msg:
            break
            
    if not video_msg:
        print(f"⚠️ [{code}] Video topilmadi (mavjud emas yoki bot javob bermadi).")
        return False
        
    raw_caption = video_msg.text or ""
    title, description = parse_movie_caption(raw_caption, code)
    print(f"🎬 [{code}] Nom: {title}")
    
    # 1. Asosiy to'liq kinoni Baza guruhiga yuborish
    baza_caption = f"🎬 <b>{title}</b>\n\n🔢 Kodi: <code>{code}</code>\n"
    if description:
        baza_caption += f"\n{description}\n"
    baza_caption += f"\n🤖 @{MY_BOT_USERNAME}"
    
    try:
        baza_msg = await client.send_file(
            BAZA_CHAT_ID,
            file=video_msg.media,
            caption=baza_caption,
            parse_mode="html"
        )
        baza_msg_id = baza_msg.id
    except Exception as e:
        print(f"❌ Baza guruhiga yuborishda xatolik: {e}")
        return False
        
    # 2. Database ga saqlash
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO movies (code, title, file_id, description, msg_id)
        VALUES (?, ?, ?, ?, ?)
    """, (str(code), title, "telethon_forwarded", description, baza_msg_id))
    conn.commit()
    conn.close()
    
    # 3. Faqat ovozli treyler videosini @kino_comfy_gr guruh/kanaliga yuborish (rasm/skrinshot yo'q)
    print(f"🎞️ [{code}] '{title}' uchun ovozli video treyler qidirilmoqda...")
    trailer_path = download_short_trailer(title, code)
    
    channel_text = f"🎬 <b>{title}</b> (Treyler)\n\n"
    if description:
        channel_text += f"{description}\n\n"
    channel_text += (
        f"🔢 <b>Kino kodi:</b> <code>{code}</code>\n\n"
        f"🍿 <b>To'liq kinoni tomosha qilish:</b>\n"
        f"👉 https://t.me/{MY_BOT_USERNAME}?start={code}"
    )
    
    if trailer_path and os.path.exists(trailer_path):
        try:
            print(f"🚀 [{code}] Ovozli treyler video @{CHANNEL_USERNAME} ga yuborilmoqda...")
            await client.send_file(
                CHANNEL_USERNAME,
                file=trailer_path,
                caption=channel_text,
                supports_streaming=True,
                parse_mode="html"
            )
            os.remove(trailer_path)
            print(f"✅ [{code}] Ovozli treyler video muvaffaqiyatli joylandi!")
        except Exception as e:
            print(f"⚠️ [{code}] Kanalga video yuborishda xatolik: {e}")
            if os.path.exists(trailer_path):
                os.remove(trailer_path)
    else:
        print(f"⚠️ [{code}] '{title}' uchun treyler topilmadi. Skrinshot yuborilmaydi (faqat video talab qilingan).")
        
    return True

async def start_scraping(start_code: int = 1, end_code: int = 50, delay_sec: int = 4):
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("Xatolik: Sessiya faol emas!")
        await client.disconnect()
        return
        
    print("="*60)
    print(f"🚀 KINO KO'CHIRISH BOSHLANDI: #{start_code} dan #{end_code} gacha")
    print("="*60)
    
    success_count = 0
    fail_count = 0
    
    for code in range(start_code, end_code + 1):
        try:
            ok = await process_movie(client, code)
            if ok:
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print(f"❌ Xatolik ({code}): {e}")
            fail_count += 1
            
        await asyncio.sleep(delay_sec)
        
    await client.disconnect()
    print("\n" + "="*60)
    print(f"🏁 TUGADI! Muvaffaqiyatli: {success_count} ta, Topilmadi/Xato: {fail_count} ta")
    print("="*60)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=1, help="Boshlang'ich kod")
    parser.add_argument("--end", type=int, default=50, help="Tugash kodi")
    args = parser.parse_args()
    
    asyncio.run(start_scraping(args.start, args.end))
