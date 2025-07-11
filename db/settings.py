# ├── db/settings.py — работа с настройками (SQLite)
import json
import sqlite3
import os
import logging
user_urls = {}

TOKEN = "7964180470:AAGVxtiEsWawT8chSeDVdF_bxpq_sjObXsk"  # <-- вставь сюда свой токен

goals = []


DB_PATH = os.path.join(os.path.dirname(__file__), 'bot.db')


SETTINGS_FILE = "settings.json"



def get_all_settings() -> dict:
    """Возвращает все настройки из файла. Создает файл, если его нет."""
    try:
        # Создаем пустой файл, если он не существует
        if not os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'w') as f:
                json.dump({}, f)

        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)

    except json.JSONDecodeError:
        return {}
    except Exception as e:
        print(f"⚠️ Ошибка загрузки настроек: {str(e)}")
        return {}

def set_setting(key: str, value: str):
    """Устанавливает значение настройки"""
    settings = get_all_settings()
    settings[key] = value
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        print(f"⚠️ Ошибка сохранения настроек: {str(e)}")

def get_target_url() -> str:
    """Возвращает сохраненный URL цели"""
    return get_all_settings().get('target_url', '')

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Создаем таблицу settings, если её нет
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                name TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        # Создаем таблицу goals, если её нет
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                url TEXT PRIMARY KEY
            )
        """)
        conn.commit()

def add_goal(url: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO goals (url) VALUES (?)", (url,))
        conn.commit()

def delete_goal(url: str):
    """
    Удаляет цель из таблицы goals и логирует, сколько строк было затронуто.
    """
    logging.getLogger(__name__).info(f"delete_goal: пытаемся удалить URL → {url}")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM goals WHERE url = ?", (url,))
        deleted = cursor.rowcount
        conn.commit()
    logging.getLogger(__name__).info(f"delete_goal: удалено строк → {deleted} для URL {url}")
    return deleted

def get_all_goals():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT url FROM goals")
        return [row[0] for row in cursor.fetchall()]

def get_setting(key: str, default=None) -> str:
    settings = get_all_settings()
    return settings.get(key, default)

# Обновляем таблицу для хранения профилей
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                profile_url TEXT PRIMARY KEY
            )
        """)
        conn.commit()



