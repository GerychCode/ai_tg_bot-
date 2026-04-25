import logging
import time # Додано
from loader import bot
import handlers
from database import init_db

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot_activity.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logger.info("Очікування ініціалізації мережі Docker (5 сек)...")
    time.sleep(5)

    logger.info("Ініціалізація бази даних...")
    init_db()

    logger.info("Бот успішно запущений (PostgreSQL + Docker)...")
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        logger.critical(f"Критична помилка під час роботи бота: {e}")