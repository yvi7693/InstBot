from db.settings import init_db
init_db()
from telebot import TeleBot, types
from db.settings import TOKEN
from ui.handlers import register_basic_handlers  # уже есть
import logging


logging.basicConfig(level=logging.INFO)
bot = TeleBot(TOKEN)
# Замените существующие структуры
monitoring_threads = {}  # Было: {chat_id: thread}
last_post_urls = {}      # Было: {chat_id: url}
# Замените текущие переменные:
  # Формат: {profile_url: {"last_post": "url", "account_rotation": [acc1, acc2]}}
current_index = 0     # Текущий индекс профиля для циклического перебора


# Регистрируем все message_handler и callback_query_handler
register_basic_handlers(bot)

# === Запуск бота ===
if __name__ == "__main__":
    print("Бот запущен...")
    bot.polling(none_stop=True)
