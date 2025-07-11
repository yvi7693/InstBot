# ├── utils/helpers.py — утилиты: валидация, emoji, логирование
import os
import re
import string
from datetime import datetime


def contains_emoji(text):
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002500-\U00002BEF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE)
    return bool(emoji_pattern.search(text))


def is_valid_login(login):
    allowed = string.ascii_letters + string.digits + "._@"
    return len(login) >= 3 and all(ch in allowed for ch in login) and not contains_emoji(login)


def is_valid_password(password):
    return len(password) >= 6 and all(ord(ch) < 128 for ch in password) and ' ' not in password and not contains_emoji(password)


def is_valid_2fa_code(code):
    return code.isdigit() and len(code) in (4, 5, 6)


def log_event(text: str, level: str = "info", logfile: str = "logs.txt"):
    try:
        with open(logfile, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{level.upper()}] {text}\n")
            f.flush()  # Принудительная запись на диск
            os.fsync(f.fileno())  # Гарантированная синхронизация
    except Exception as e:
        print(f"[LOGGING ERROR] {e}")
