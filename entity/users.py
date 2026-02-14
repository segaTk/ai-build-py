import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import os
from dotenv import load_dotenv

load_dotenv()


DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASS"),
}

# Проверка обязательных параметров
if not DB_CONFIG["password"]:
    raise ValueError("❌ Переменная окружения DB_PASS не установлена!")

@contextmanager
def get_db_connection():
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()

def save_user(user_data: dict):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO telegram_users (
                    id, username, first_name, last_name, 
                    language_code, is_premium, has_subscription, last_seen
                ) VALUES (
                    %(id)s, %(username)s, %(first_name)s, %(last_name)s,
                    %(language_code)s, %(is_premium)s, NOW()
                )
                ON CONFLICT (id) DO UPDATE SET
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    language_code = EXCLUDED.language_code,
                    is_premium = EXCLUDED.is_premium,
                    last_seen = NOW()
            """, user_data)
            conn.commit()


def save_subscription(user_id: int):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE telegram_users SET has_subscription = TRUE WHERE id = %s",
                (user_id,)
            )
            conn.commit()

def has_subscription(user_id: int) -> bool:
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT has_subscription FROM telegram_users WHERE id = %s",
                (user_id,)
            )
            row = cur.fetchone()
            return bool(row["has_subscription"]) if row else False

