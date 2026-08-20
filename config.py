import os
from dotenv import load_dotenv

load_dotenv()  # .env faylidan o'qiydi (agar mavjud bo'lsa)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
DB_PATH = os.environ.get("DB_PATH", "planbot.db")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN topilmadi! .env faylida yoki muhit o'zgaruvchisida "
        "TELEGRAM_BOT_TOKEN ni belgilang."
    )
if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY topilmadi! .env faylida yoki muhit o'zgaruvchisida "
        "GEMINI_API_KEY ni belgilang."
    )
