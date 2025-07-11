import csv
import os
import random
from typing import List
import time
import logging

COMMENTS_DB = "comments_db.csv"
COMMENT_LOG = "comment_log.csv"

def get_custom_comment() -> str:
    """Возвращает случайный комментарий из файла"""
    try:
        with open(COMMENTS_DB, 'r', encoding='utf-8') as f:
            comments = [line.strip() for line in f.readlines()[1:] if line.strip()]
            return random.choice(comments) if comments else ""
    except Exception as e:
        logging.error(f"Ошибка чтения комментариев: {str(e)}")
        return ""

def add_comments(comments: List[str]):
    # Создаем файл если не существует
    if not os.path.exists(COMMENTS_DB):
        with open(COMMENTS_DB, "w", encoding="utf-8") as f:
            f.write("comment\n")

    # Добавляем новые комментарии
    existing = set()
    with open(COMMENTS_DB, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        existing = {row['comment'] for row in reader}

    new_comments = [c for c in comments if c not in existing]

    with open(COMMENTS_DB, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for comment in new_comments:
            writer.writerow([comment])


def get_random_comment() -> str:
    if not os.path.exists(COMMENTS_DB):
        return ""

    with open(COMMENTS_DB, "r", encoding="utf-8") as f:
        comments = [row[0] for row in csv.reader(f)][1:]  # Пропускаем заголовок

    return random.choice(comments) if comments else ""


def log_comment_stat(username: str, media_pk: str, comment_text: str):
    file_exists = os.path.isfile(COMMENT_LOG)
    with open(COMMENT_LOG, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "username", "media_pk", "comment"])
        writer.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), username, media_pk, comment_text])


def get_comment_stats_text() -> str:
    if not os.path.exists(COMMENT_LOG):
        return "📊 Статистика пуста"

    with open(COMMENT_LOG, "r", encoding="utf-8") as f:
        total = sum(1 for line in f) - 1  # исключаем заголовок

    return f"📊 Всего комментариев отправлено: {total}"


def get_all_comments() -> list:
    """Возвращает все загруженные комментарии из базы"""
    if not os.path.exists(COMMENTS_DB):
        return []

    with open(COMMENTS_DB, "r", encoding="utf-8") as f:
        return [row[0] for row in csv.reader(f)][1:]  # Пропускаем заголовок
# [file content end]

# [file name]: selenium_auth.py (обновленная функция post_comment)
# [file content begin]

# В comments_file.py
def reset_comment_stats():
    if os.path.exists(COMMENT_LOG):
        os.remove(COMMENT_LOG)

def delete_comment(comment: str) -> bool:
    """Удаляет комментарий из базы. Возвращает True, если удалено хотя бы одно вхождение"""
    if not os.path.exists(COMMENTS_DB):
        return False

    with open(COMMENTS_DB, "r", encoding="utf-8") as f:
        rows = [row for row in csv.reader(f)]

    header, data = rows[0], rows[1:]
    filtered = [row for row in data if row[0] != comment]

    if len(filtered) == len(data):
        return False

    with open(COMMENTS_DB, "w", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(filtered)

    return True

def delete_all_comments() -> bool:
    """Удаляет все комментарии из базы"""
    if not os.path.exists(COMMENTS_DB):
        return False
    try:
        os.remove(COMMENTS_DB)
        # Создаем пустой файл с заголовком
        with open(COMMENTS_DB, 'w', encoding='utf-8') as f:
            f.write("comment\n")
        return True
    except Exception as e:
        logging.error(f"Error deleting all comments: {e}")
        return False