import os
import sys
from dotenv import load_dotenv

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="ignore")

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = os.getenv("ADMIN_ID", "").strip()

try:
    ADMIN_IDS = [int(i.strip()) for i in ADMIN_ID.split(",") if i.strip().isdigit()]
except Exception:
    ADMIN_IDS = []

if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
    print("OGOHLANTIRISH: .env fayliga haqiqiy Telegram Bot Token kiritilmagan!")
