import os
import sys
from dotenv import load_dotenv, set_key

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="ignore")

ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(ENV_PATH)

BOT_TOKEN = os.getenv("BOT_TOKEN", "8794577340:AAFSE5BQIolYxfrqNfiGcszWgsEbs1xn3L0").strip()
ADMIN_ID = os.getenv("ADMIN_ID", "7909677265").strip()
BAZA_ID = os.getenv("BAZA_ID", "-1004294509106").strip()

try:
    ADMIN_IDS = [int(i.strip()) for i in ADMIN_ID.split(",") if i.strip().isdigit()]
except Exception:
    ADMIN_IDS = []

if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
    print("OGOHLANTIRISH: .env fayliga haqiqiy Telegram Bot Token kiritilmagan!")

def get_channels():
    """Kanallar ro'yxatini .env dan o'qiydi"""
    raw = os.getenv("CHANNELS", "@kino_comfy_gr|https://t.me/kino_comfy_gr|KINO comfy").strip()
    if not raw:
        return []
    channels = []
    for entry in raw.split(","):
        parts = entry.strip().split("|")
        if len(parts) == 3:
            channels.append((parts[0].strip(), parts[1].strip(), parts[2].strip()))
    return channels

def save_channels(channels: list):
    """Kanallar ro'yxatini .env ga yozadi"""
    raw = ",".join(f"{ch[0]}|{ch[1]}|{ch[2]}" for ch in channels)
    set_key(ENV_PATH, "CHANNELS", raw)
    # runtime da ham yangilaymiz
    os.environ["CHANNELS"] = raw

def add_channel(channel_id: str, channel_url: str, title: str) -> bool:
    """Yangi kanal qo'shadi"""
    channels = get_channels()
    # Agar allaqachon borsa, yangilaymiz
    channels = [ch for ch in channels if ch[0] != channel_id.strip()]
    channels.append((channel_id.strip(), channel_url.strip(), title.strip()))
    save_channels(channels)
    return True

def delete_channel(channel_id: str):
    """Kanal o'chiradi"""
    channels = get_channels()
    channels = [ch for ch in channels if ch[0] != channel_id.strip()]
    save_channels(channels)
