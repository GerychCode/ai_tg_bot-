import psycopg2
from psycopg2.extras import RealDictCursor
import json
import logging
from config import DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME, ADMIN_ID

logger = logging.getLogger(__name__)


def get_connection():
    try:
        return psycopg2.connect(
            host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, dbname=DB_NAME,
            cursor_factory=RealDictCursor  # Усі результати будуть у вигляді словників
        )
    except Exception as e:
        logger.error(f"Помилка підключення до БД: {e}")
        return None


def init_db():
    conn = get_connection()
    if not conn: return
    try:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username VARCHAR(255),
                    state VARCHAR(50) DEFAULT NULL,
                    state_data JSONB DEFAULT '{}'
                )
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255),
                    price VARCHAR(50),
                    price_api INTEGER,
                    description TEXT
                )
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    username VARCHAR(255),
                    item_name VARCHAR(255),
                    contact TEXT,
                    status VARCHAR(50)
                )
            ''')

            # Нова таблиця для відгуків
            cur.execute('''
                CREATE TABLE IF NOT EXISTS feedbacks (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    username VARCHAR(255),
                    text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Додаємо тестові товари, якщо таблиця порожня
            cur.execute('SELECT COUNT(*) FROM products')
            if cur.fetchone()['count'] == 0:
                cur.execute(
                    "INSERT INTO products (name, price, price_api, description) VALUES ('Ноутбук Pro 15', '35000 грн', 3500000, 'Потужний ноутбук для роботи.')")
                cur.execute(
                    "INSERT INTO products (name, price, price_api, description) VALUES ('Смартфон X-Phone', '22000 грн', 2200000, 'Чудова камера та OLED дисплей.')")
        conn.commit()
    finally:
        conn.close()


# --- СТАНИ КОРИСТУВАЧІВ (FSM) ---
def set_user_state(user_id, state, state_data=None, username=""):
    conn = get_connection()
    if not conn: return
    try:
        with conn.cursor() as cur:
            data_json = json.dumps(state_data) if state_data else '{}'
            cur.execute('''
                INSERT INTO users (user_id, username, state, state_data) 
                VALUES (%s, %s, %s, %s) 
                ON CONFLICT (user_id) DO UPDATE 
                SET state = EXCLUDED.state, state_data = EXCLUDED.state_data, username = EXCLUDED.username
            ''', (user_id, username, state, data_json))
        conn.commit()
    finally:
        conn.close()


def get_user_state(user_id):
    conn = get_connection()
    if not conn: return None, {}
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT state, state_data FROM users WHERE user_id = %s', (user_id,))
            res = cur.fetchone()
            if res:
                return res['state'], res['state_data'] or {}
            return None, {}
    finally:
        conn.close()


def clear_user_state(user_id):
    set_user_state(user_id, None, {})


# --- ТОВАРИ ---
def get_all_products():
    conn = get_connection()
    if not conn: return []
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM products ORDER BY id')
            return cur.fetchall()
    finally:
        conn.close()


def get_product(product_id):
    conn = get_connection()
    if not conn: return None
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM products WHERE id = %s', (product_id,))
            return cur.fetchone()
    finally:
        conn.close()


def add_product(name, price, price_api, description):
    conn = get_connection()
    if not conn: return
    try:
        with conn.cursor() as cur:
            cur.execute('INSERT INTO products (name, price, price_api, description) VALUES (%s, %s, %s, %s)',
                        (name, price, price_api, description))
        conn.commit()
    finally:
        conn.close()


def delete_product(product_id):
    conn = get_connection()
    if not conn: return
    try:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM products WHERE id = %s', (product_id,))
        conn.commit()
    finally:
        conn.close()


# --- ЗАМОВЛЕННЯ ---
def add_order(user_id, username, item_name, contact, status):
    conn = get_connection()
    if not conn: return None
    try:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO orders (user_id, username, item_name, contact, status) 
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            ''', (user_id, username, item_name, contact, status))
            order_id = cur.fetchone()['id']
        conn.commit()
        return order_id
    finally:
        conn.close()


def update_order_status(order_id, new_status):
    conn = get_connection()
    if not conn: return
    try:
        with conn.cursor() as cur:
            cur.execute('UPDATE orders SET status = %s WHERE id = %s', (new_status, order_id))
        conn.commit()
    finally:
        conn.close()


def get_orders(active=True):
    conn = get_connection()
    if not conn: return []
    try:
        with conn.cursor() as cur:
            if active:
                cur.execute("SELECT * FROM orders WHERE status != 'Виконано' ORDER BY id DESC")
            else:
                cur.execute("SELECT * FROM orders WHERE status = 'Виконано' ORDER BY id DESC LIMIT 50")
            return cur.fetchall()
    finally:
        conn.close()


# --- ВІДГУКИ ---
def add_feedback(user_id, username, text):
    conn = get_connection()
    if not conn: return
    try:
        with conn.cursor() as cur:
            cur.execute('INSERT INTO feedbacks (user_id, username, text) VALUES (%s, %s, %s)',
                        (user_id, username, text))
        conn.commit()
    finally:
        conn.close()


def get_all_feedbacks():
    conn = get_connection()
    if not conn: return []
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM feedbacks ORDER BY id DESC LIMIT 20')
            return cur.fetchall()
    finally:
        conn.close()


def is_admin(user_id):
    return str(user_id) == str(ADMIN_ID)