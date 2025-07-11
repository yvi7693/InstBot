# ├── db/comments.py — работа с комментариями (SQLite)

import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
import csv
import os
import random
import time


DB_PATH = os.getenv("COMMENTS_DB", "bot_data.db")

def get_comment_stats_text(log_file="comment_log.csv"):
    if not os.path.exists(log_file):
        return "Пока нет данных по комментариям."

    stats = defaultdict(lambda: defaultdict(int))
    with open(log_file, "r", encoding="utf-8") as f:
        from csv import reader
        for row in reader(f):
            try:
                timestamp, username, media_pk, comment_text = row
                date = timestamp.split("T")[0]
                stats[username][date] += 1
            except ValueError:
                continue  # Пропускаем некорректные строки

    text = "📊 Статистика комментариев:\n\n"
    for username, dates in stats.items():
        total = sum(dates.values())
        weekly = sum(
            count for date_str, count in dates.items()
            if datetime.fromisoformat(date_str) >= datetime.now() - timedelta(days=7)
        )
        text += f"👤 {username}:\n"
        text += f"  - За всё время: {total}\n"
        text += f"  - За 7 дней: {weekly}\n"
        text += "\n".join([f"    {date}: {count}" for date, count in sorted(dates.items(), reverse=True)])
        text += "\n\n"
    return text

def init_comments_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL
            )
        """)
        conn.commit()

def init_comments_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL
            )
        """)
        conn.commit()


def insert_comment(text):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO comments (text) VALUES (?)", (text,))
        conn.commit()


def delete_comment(comment_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
        conn.commit()


def filter_comments(keyword):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, text FROM comments WHERE LOWER(text) LIKE ?", (f"%{keyword.lower()}%",))
        return cursor.fetchall()


def get_all_comments(limit=50):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, text FROM comments LIMIT ?", (limit,))
        return cursor.fetchall()


def log_comment_stat(username, media_pk, comment_text, log_file="comment_log.csv"):
    with open(log_file, "a", encoding="utf-8", newline="") as f:
        from csv import writer
        writer(f).writerow([datetime.now().isoformat(), username, media_pk, comment_text])




