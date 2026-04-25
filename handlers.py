import logging
from google import genai
from google.genai import types
from telebot.types import LabeledPrice, ShippingOption, InlineKeyboardMarkup, InlineKeyboardButton
from loader import bot
from config import PROVIDER_TOKEN, ADMIN_ID, GEMINI_API_KEY
from database import (
    is_admin, get_all_products, get_product, add_product, delete_product,
    add_order, get_orders, update_order_status, set_user_state, get_user_state,
    clear_user_state, add_feedback, get_all_feedbacks
)
from keyboards import get_main_menu, get_catalog_keyboard, get_buy_keyboard, get_payment_choice_keyboard

logger = logging.getLogger(__name__)

# --- Ініціалізація ШІ ---
if GEMINI_API_KEY:
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    ai_client = None
    logger.warning("GEMINI_API_KEY не знайдено. ШІ-консультант не працюватиме.")


# --- ПАНЕЛЬ АДМІНІСТРАТОРА ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_admin(message.from_user.id): return
    admin_text = (
        "🛠 <b>Панель адміністратора</b>\n\n"
        "➕ /add_item — Додати товар\n"
        "➖ /remove_item — Видалити товар\n\n"
        "📋 /orders — Активні замовлення\n"
        "📦 /completed_orders — Виконані замовлення\n"
        "💬 /feedbacks — Переглянути відгуки"
    )
    bot.send_message(message.chat.id, admin_text, parse_mode="HTML")


@bot.message_handler(commands=['orders'])
def view_active_orders(message):
    if not is_admin(message.from_user.id): return
    orders = get_orders(active=True)
    if not orders:
        bot.send_message(message.chat.id, "📭 Немає активних замовлень.")
        return
    bot.send_message(message.chat.id, "📋 <b>Активні замовлення:</b>", parse_mode="HTML")
    for order in orders:
        text = f"🔹 <b>Замовлення #{order['id']}</b>\n👤 Клієнт: {order['username']}\n📦 Товар: {order['item_name']}\n📞 Контакт: {order['contact']}\nℹ️ Статус: {order['status']}"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ Підтвердити відправку", callback_data=f"finish_order_{order['id']}"))
        bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)


@bot.message_handler(commands=['completed_orders'])
def view_completed_orders(message):
    if not is_admin(message.from_user.id): return
    orders = get_orders(active=False)
    if not orders:
        bot.send_message(message.chat.id, "📭 Список виконаних замовлень порожній.")
        return
    text = "📦 <b>Виконані замовлення:</b>\n\n"
    for order in orders:
        text += f"🔹 <b>#{order['id']}</b> | {order['username']} | {order['item_name']} | <i>{order['status']}</i>\n"
    bot.send_message(message.chat.id, text[:4000], parse_mode="HTML")


@bot.message_handler(commands=['feedbacks'])
def view_feedbacks(message):
    if not is_admin(message.from_user.id): return
    feedbacks = get_all_feedbacks()
    if not feedbacks:
        bot.send_message(message.chat.id, "📭 Відгуків ще немає.")
        return
    text = "💬 <b>Останні відгуки:</b>\n\n"
    for f in feedbacks:
        date_str = str(f['created_at'])[:16] if f.get('created_at') else ""
        text += f"👤 <b>{f['username']}</b> <i>({date_str})</i>:\n{f['text']}\n\n"
    bot.send_message(message.chat.id, text[:4000], parse_mode="HTML")


@bot.message_handler(commands=['add_item'])
def add_item_start(message):
    if not is_admin(message.from_user.id): return
    set_user_state(message.chat.id, 'admin_add_name')
    bot.send_message(message.chat.id, "✏️ Введіть назву нового товару:")


@bot.message_handler(commands=['remove_item'])
def remove_item_start(message):
    if not is_admin(message.from_user.id): return
    markup = InlineKeyboardMarkup()
    products = get_all_products()
    for product in products:
        markup.add(InlineKeyboardButton(text=f"❌ Видалити: {product['name']}", callback_data=f"del_{product['id']}"))
    bot.send_message(message.chat.id, "🗑 Оберіть товар для видалення:", reply_markup=markup)


# --- ОСНОВНІ КОМАНДИ ---
@bot.message_handler(commands=['start', 'help', 'info'])
def handle_basic_commands(message):
    clear_user_state(message.chat.id)
    if message.text == '/start':
        bot.send_message(message.chat.id, "👋 Вітаю! Скористайтеся меню нижче.", reply_markup=get_main_menu())
    else:
        bot.send_message(message.chat.id, "🤖 Я бот-магазин. Використовуйте кнопки для навігації.")


@bot.message_handler(commands=['catalog'])
def show_catalog(message):
    clear_user_state(message.chat.id)
    bot.send_message(message.chat.id, "📦 <b>Каталог товарів</b>\nОберіть товар:", parse_mode="HTML",
                     reply_markup=get_catalog_keyboard())


@bot.message_handler(commands=['order'])
def start_order(message):
    set_user_state(message.chat.id, 'waiting_for_order_item')
    bot.send_message(message.chat.id, "📦 Напишіть, що саме ви хочете замовити:")


@bot.message_handler(commands=['feedback'])
def ask_feedback(message):
    username = message.from_user.username or message.from_user.first_name
    set_user_state(message.chat.id, 'waiting_for_feedback', username=username)
    bot.send_message(message.chat.id, "✍️ Напишіть ваш відгук.")


# --- ОБРОБКА ІНЛАЙН-КНОПОК ---
@bot.callback_query_handler(func=lambda call: True)
def handle_inline_clicks(call):
    data = call.data
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    user = call.from_user
    username = f"@{user.username}" if user.username else user.first_name

    if data.startswith('del_'):
        if is_admin(user.id):
            pid = int(data.split('_')[1])
            delete_product(pid)
            bot.edit_message_text("✅ Товар видалено.", chat_id, message_id)

    elif data.startswith('finish_order_'):
        if is_admin(user.id):
            order_id = int(data.split('_')[2])
            update_order_status(order_id, "Виконано")
            bot.edit_message_text(f"{call.message.text}\n\n✅ <b>ВІДПРАВЛЕНО / ВИКОНАНО</b>", chat_id, message_id,
                                  parse_mode="HTML")

    elif data.startswith('prod_'):
        product_id = int(data.split('_')[1])
        product = get_product(product_id)
        if product:
            bot.send_message(chat_id,
                             f"🔎 <b>{product['name']}</b>\n💰 Ціна: {product['price']}\n📝 Опис: {product['description']}",
                             parse_mode="HTML", reply_markup=get_buy_keyboard(product['id']))

    elif data.startswith('askai_'):
        product_id = int(data.split('_')[1])
        product = get_product(product_id)

        if not ai_client:
            bot.send_message(chat_id, "⚠️ ШІ-консультант зараз вимкнений (немає ключа API).")
            bot.answer_callback_query(call.id)
            return

        set_user_state(chat_id, 'waiting_for_ai_question', state_data={
            'product_name': product['name'],
            'product_desc': product['description']
        })
        bot.send_message(chat_id,
                         f"🤖 <b>ШІ-Консультант</b>\n\nВи обрали: <b>{product['name']}</b>.\nНапишіть ваше питання про цей товар:",
                         parse_mode="HTML")

    elif data.startswith('buy_'):
        product_id = data.split('_')[1]
        bot.edit_message_text("💳 Оберіть спосіб оформлення замовлення:", chat_id, message_id,
                              reply_markup=get_payment_choice_keyboard(product_id))

    elif data.startswith('paycash_'):
        product_id = int(data.split('_')[1])
        product = get_product(product_id)

        order_id = add_order(user.id, username, product['name'], f"ID: {user.id}", "Оплата при отриманні")
        bot.edit_message_text("✅ Замовлення оформлене! Адміністратор зв'яжеться з вами.", chat_id, message_id)

        if ADMIN_ID:
            bot.send_message(ADMIN_ID,
                             f"🚨 <b>НОВЕ ЗАМОВЛЕННЯ #{order_id}</b>\n👤 Клієнт: {username}\n📦 Товар: {product['name']}\n💵 Тип: При отриманні",
                             parse_mode="HTML")

    elif data.startswith('paymock_'):
        product_id = int(data.split('_')[1])
        product = get_product(product_id)

        set_user_state(chat_id, 'mock_address', state_data={'product_id': product_id, 'product_name': product['name']})

        bot.edit_message_text(f"🛠 <b>ІМІТАЦІЯ ОПЛАТИ</b> 🛠\n📍 Введіть <b>ПІБ, місто та відділення НП</b>:", chat_id,
                              message_id, parse_mode="HTML")

    elif data.startswith('payonline_'):
        product_id = int(data.split('_')[1])
        product = get_product(product_id)
        bot.delete_message(chat_id, message_id)
        prices = [LabeledPrice(label=product['name'], amount=product['price_api'])]
        bot.send_invoice(
            chat_id, title=product['name'], description=product['description'],
            invoice_payload=f"invoice_{product['id']}",
            provider_token=PROVIDER_TOKEN, currency='UAH', prices=prices, start_parameter=f"pay_{product['id']}",
            need_name=True, need_phone_number=True, need_shipping_address=True, is_flexible=True
        )

    elif data == 'cancel':
        bot.edit_message_text("❌ Дію скасовано.", chat_id, message_id)

    bot.answer_callback_query(call.id)


# --- ПЛАТІЖНА СИСТЕМА ---
@bot.shipping_query_handler(func=lambda query: True)
def shipping(shipping_query):
    address = shipping_query.shipping_address
    if address.country_code != 'UA':
        bot.answer_shipping_query(shipping_query.id, ok=False, error_message='Тільки Україна 🇺🇦.')
        return
    options = [ShippingOption(id='nova_poshta', title='Нова Пошта').add_price(LabeledPrice('Доставка', 10000))]
    bot.answer_shipping_query(shipping_query.id, ok=True, shipping_options=options)


@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    payment_info = message.successful_payment
    product_id = int(payment_info.invoice_payload.split('_')[1])
    product = get_product(product_id) or {"name": "Невідомий товар"}
    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
    order_info = payment_info.order_info
    contact = f"{order_info.phone_number} ({order_info.name})"

    order_id = add_order(message.from_user.id, username, product['name'], contact, "ОПЛАЧЕНО ОНЛАЙН")

    bot.send_message(message.chat.id, f"🎉 Ваше замовлення #{order_id} успішно прийнято.")
    if ADMIN_ID:
        bot.send_message(ADMIN_ID,
                         f"🚨 <b>УСПІШНА ОПЛАТА #{order_id}</b> 🚨\n👤 Клієнт: {username}\n📦 Товар: {product['name']}",
                         parse_mode="HTML")


# --- ОБРОБКА ТЕКСТОВИХ ПОВІДОМЛЕНЬ (FSM з БД) ---
@bot.message_handler(content_types=['text'])
def handle_text(message):
    chat_id = message.chat.id
    username = message.from_user.username or message.from_user.first_name

    state, state_data = get_user_state(chat_id)

    if state == 'admin_add_name':
        set_user_state(chat_id, 'admin_add_price', state_data={'new_name': message.text})
        bot.send_message(chat_id, "💰 Введіть ціну (ТІЛЬКИ цифри):")

    elif state == 'admin_add_price':
        if not message.text.isdigit():
            bot.send_message(chat_id, "❌ Тільки цифри! Спробуйте ще раз:")
            return
        state_data.update({'new_price': f"{message.text} грн", 'new_price_api': int(message.text) * 100})
        set_user_state(chat_id, 'admin_add_desc', state_data=state_data)
        bot.send_message(chat_id, "📝 Введіть опис:")

    elif state == 'admin_add_desc':
        add_product(state_data['new_name'], state_data['new_price'], state_data['new_price_api'], message.text)
        bot.send_message(chat_id, f"✅ Товар успішно збережено в БД!")
        clear_user_state(chat_id)

    elif state == 'waiting_for_order_item':
        set_user_state(chat_id, 'waiting_for_order_contact', state_data={'order_item': message.text})
        bot.send_message(chat_id, "📞 Вкажіть ваш номер телефону:")

    elif state == 'waiting_for_order_contact':
        item_name = state_data.get('order_item', 'Не вказано')
        add_order(message.from_user.id, username, item_name, message.text, "Ручне замовлення")
        bot.send_message(chat_id, "✅ Замовлення збережено в БД!")
        clear_user_state(chat_id)

    elif state == 'waiting_for_feedback':
        add_feedback(message.from_user.id, username, message.text)
        bot.send_message(chat_id, "✅ Дякуємо за ваш відгук! Ми його отримали та зберегли.")
        clear_user_state(chat_id)
        if ADMIN_ID:
            bot.send_message(ADMIN_ID, f"📨 <b>НОВИЙ ВІДГУК</b>\n👤 Від: @{username}\n💬 Текст: {message.text}",
                             parse_mode="HTML")

    elif state == 'mock_address':
        product_name = state_data.get('product_name', 'Невідомо')
        order_id = add_order(message.from_user.id, username, product_name, message.text, "ОПЛАЧЕНО (Тест)")

        bot.send_message(chat_id, f"✅ <b>Тестова оплата пройшла успішно!</b>\n\nЗамовлення #{order_id} прийнято.",
                         parse_mode="HTML")
        clear_user_state(chat_id)

        if ADMIN_ID:
            bot.send_message(ADMIN_ID,
                             f"🚨 <b>ТЕСТОВЕ ЗАМОВЛЕННЯ #{order_id}</b>\n👤 Клієнт: {username}\n📦 Товар: {product_name}\n📍 Дані: {message.text}",
                             parse_mode="HTML")

    # --- ЗАПИТ ДО ШІ-КОНСУЛЬТАНТА ---
    elif state == 'waiting_for_ai_question':
        if not ai_client:
            bot.send_message(chat_id, "ШІ тимчасово недоступний.")
            clear_user_state(chat_id)
            return

        product_name = state_data.get('product_name', 'Невідомий товар')
        product_desc = state_data.get('product_desc', 'Опис відсутній')
        question = message.text

        bot.send_chat_action(chat_id, 'typing')

        prompt = f"""
        Ти ввічливий і компетентний продавець-консультант інтернет-магазину.
        Клієнт цікавиться товаром: "{product_name}".
        Опис цього товару в нашій базі: "{product_desc}".

        Питання клієнта: "{question}"

        Твоя задача: Дай коротку, точну та привітну відповідь українською мовою. 
        Якщо в описі з бази достатньо інформації - відповідай по ньому. 
        Якщо клієнт питає про детальні характеристики (яких немає в описі), відгуки в мережі, сумісність або порівняння — ОБОВ'ЯЗКОВО ВИКОРИСТОВУЙ ПОШУК В ІНТЕРНЕТІ, щоб знайти актуальну інформацію про цей товар.
        Якщо питання стосується наявності саме в нашому магазині чи умов доставки — запропонуй звернутися до живого менеджера.
        Не вигадуй факти, спирайся тільки на опис бази або результати інтернет-пошуку.
        """

        try:
            response = ai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[{"google_search": {}}]
                )
            )
            bot.send_message(chat_id, f"🤖 <b>ШІ-Консультант:</b>\n\n{response.text}", parse_mode="HTML")
            bot.send_message(chat_id,
                             "<i>Можете задати ще питання по цьому товару, або оберіть /catalog для виходу.</i>",
                             parse_mode="HTML")
        except Exception as e:
            logger.error(f"Помилка Gemini API: {e}")
            bot.send_message(chat_id, "Вибачте, виникла технічна помилка ШІ. Спробуйте трохи пізніше.")

    else:
        if message.text.startswith('/'):
            bot.send_message(chat_id, "❌ Невідома команда.")
        else:
            bot.send_message(chat_id, "Скористайтеся меню кнопок знизу.")