import sqlite3

DB_PATH = "bot.db"

def init_db():
    """
    Создаёт базу данных и таблицу настроек, если её нет.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            value TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_all_settings():
    """
    Возвращает все настройки в виде словаря.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, value FROM settings")
    rows = cursor.fetchall()
    conn.close()
    return {name: value for name, value in rows}

def get_setting(name):
    """
    Получает значение настройки по имени.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE name = ?", (name,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def set_setting(name, value):
    """
    Устанавливает или обновляет настройку.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO settings (name, value) 
        VALUES (?, ?)
        ON CONFLICT(name) DO UPDATE SET value = excluded.value
    ''', (name, value))
    conn.commit()
    conn.close()