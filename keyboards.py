from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_all_products
from config import PROVIDER_TOKEN

def get_main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        KeyboardButton('/start'),
        KeyboardButton('/catalog'),
        KeyboardButton('/order'),
        KeyboardButton('/feedback')
    )
    return markup

def get_catalog_keyboard():
    markup = InlineKeyboardMarkup()
    products = get_all_products()
    for product in products:
        markup.add(InlineKeyboardButton(
            text=f"{product['name']} — {product['price']}",
            callback_data=f"prod_{product['id']}"
        ))
    return markup

def get_buy_keyboard(product_id):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🛒 Купити", callback_data=f"buy_{product_id}"),
        InlineKeyboardButton("🤖 Запитати ШІ про товар", callback_data=f"askai_{product_id}") # ДОДАНО
    )
    return markup

def get_payment_choice_keyboard(product_id):
    markup = InlineKeyboardMarkup(row_width=1)
    if PROVIDER_TOKEN:
        markup.add(InlineKeyboardButton("💳 Оплатити онлайн (Telegram)", callback_data=f"payonline_{product_id}"))
    else:
        markup.add(InlineKeyboardButton("💳 Оплатити онлайн (ІМІТАЦІЯ)", callback_data=f"paymock_{product_id}"))
    markup.add(
        InlineKeyboardButton("💵 Оплата при отриманні", callback_data=f"paycash_{product_id}"),
        InlineKeyboardButton("❌ Скасувати", callback_data="cancel")
    )
    return markup