import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ.get('BOT_TOKEN')
PROVIDER_TOKEN = os.environ.get('PROVIDER_TOKEN')
ADMIN_ID = os.environ.get('ADMIN_ID', "576542169")
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

DB_HOST = os.environ.get('DB_HOST', 'db')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_USER = os.environ.get('DB_USER', 'bot_admin')
DB_PASS = os.environ.get('DB_PASS', 'bot_password')
DB_NAME = os.environ.get('DB_NAME', 'bot_database')

if not BOT_TOKEN:
    raise ValueError("Помилка: Токен бота не знайдено.")