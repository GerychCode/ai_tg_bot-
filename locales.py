from database import get_user_lang

TRANSLATIONS = {
    'uk': {
        'welcome': "👋 Вітаю! Скористайтеся меню нижче.",
        'catalog': "📦 <b>Каталог товарів</b>\nОберіть товар:",
        'feedback_prompt': "✍️ Напишіть ваш відгук.",
        'feedback_thanks': "✅ Дякуємо за ваш відгук! Ми його отримали.",
    },
    'en': {
        'welcome': "👋 Hello! Please use the menu below.",
        'catalog': "📦 <b>Product Catalog</b>\nChoose an item:",
        'feedback_prompt': "✍️ Please write your feedback.",
        'feedback_thanks': "✅ Thank you for your feedback! We have received it.",
    }
}

def _(text_key, user_id):
    """Отримує переклад для конкретного користувача"""
    lang = get_user_lang(user_id)
    return TRANSLATIONS.get(lang, TRANSLATIONS['uk']).get(text_key, f"_{text_key}_")