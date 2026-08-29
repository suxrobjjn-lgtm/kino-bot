import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiohttp import web

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="ignore")

from config import BOT_TOKEN
from handlers import router
from admin_handlers import admin_router
import database as db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

async def handle_ping(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_get("/health", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    db.init_db()
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("\n" + "=" * 60)
        print("XATOLIK: Bot Token kiritilmagan!")
        print("Iltimos, '.env' faylini ochib, BOT_TOKEN ga Telegram @BotFather dan olgan tokeningizni yozing.")
        print("Misol: BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
        print("=" * 60 + "\n")
        return

    try:
        await start_web_server()
    except Exception as e:
        logging.warning(f"Web server xatosi: {e}")

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.include_router(admin_router)
    dp.include_router(router)

    print("\n" + "=" * 60)
    print("Telegram Bot muvaffaqiyatli ishga tushdi!")
    print("Botni to'xtatish uchun: Ctrl + C bosing")
    print("=" * 60 + "\n")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\nBot to'xtatildi.")

