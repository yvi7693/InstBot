import random
from datetime import datetime

EMOJIS = ["🔥", "👍", "💯", "😁", "🎉", "❤️", "😍", "😎"]

COMMENTS_BY_TIME = {
    'morning': ["Доброе утро ☀️", "Какое прекрасное утро! 🌼", "С добрым утром! 😊"],
    'day':     ["Хорошего дня! 😎", "Крутой пост! 🔥", "Супер фото! 👍"],
    'evening': ["Вечер в кайф! 🌆", "Отличный пост! 🌙", "Приятного вечера! 🌃"],
    'night':   ["Спокойной ночи 🌙", "Уютной ночи ✨", "Сладких снов 😴"]
}

COMMENT_TEMPLATES = [
    "Отличный пост! {emoji}",
    "Очень круто получилось! {emoji}",
    "Интересная публикация {emoji}",
    "Спасибо за полезную информацию {emoji}",
    "Очень понравилось {emoji} Ждём новых постов!",
]

COMMENTING_HOURS = (8, 22)

def get_time_period():
    hour = datetime.now().hour
    if 6 <= hour < 12:
        return 'morning'
    elif 12 <= hour < 18:
        return 'day'
    elif 18 <= hour < 23:
        return 'evening'
    else:
        return 'night'

def random_comment():
    period = get_time_period()
    comment = random.choice(COMMENTS_BY_TIME.get(period, ["Прекрасный день!"]))
    emoji = random.choice(EMOJIS)
    return f"{comment} {emoji}"

def random_template_comment():
    template = random.choice(COMMENT_TEMPLATES)
    emoji = random.choice(EMOJIS)
    return template.format(emoji=emoji)

def is_within_commenting_hours():
    now = datetime.now().hour
    return 0 <= now <= 23
