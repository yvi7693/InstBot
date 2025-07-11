# ├── menus.py — кнопки и меню Telegram
import types

from telebot import TeleBot
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

def admin_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Добавить аккаунт", "📥 Управление комментариями")
    markup.add("🎯 Управление целями", "▶️ Старт", "⏹️ Стоп")
    markup.add("🕒 Настроить расписание", "⚙️ Настройки")
    markup.add("📊 Статистика", "📜 Логи")
    return markup


def back_button_markup():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add("⬅️ Назад")
    return kb


def send_settings_menu(bot, chat_id, settings, message_id=None):
    if not settings:
        bot.send_message(chat_id, "⚙️ Настройки не найдены.")
        return

    markup = InlineKeyboardMarkup(row_width=2)

    # Добавляем наши новые пункты:
    markup.row(
        InlineKeyboardButton("💬 Посмотреть комментарии", callback_data="view_comments"),
        InlineKeyboardButton("📜 Логи", callback_data="view_logs")
    )
    markup.row(
        InlineKeyboardButton("📊 Стата коммов", callback_data="view_stats")
    )
    markup.add(InlineKeyboardButton("🔙 Назад", callback_data="settings_back"))

    if message_id:
        bot.edit_message_text("⚙️ Настройки бота:", chat_id, message_id, reply_markup=markup)
    else:
        bot.send_message(chat_id, "⚙️ Настройки бота:", reply_markup=markup)

    markup = InlineKeyboardMarkup(row_width=1)
    for name, value in settings.items():
        markup.add(InlineKeyboardButton(f"{name}: {value}", callback_data=f"edit_setting:{name}"))

    markup.add(InlineKeyboardButton("🔙 Назад", callback_data="settings_back"))


def create_goal_buttons(goals: list) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    for goal in goals:
        goal_id = goal.get('id')
        goal_title = goal.get('title', 'Цель')
        if not goal_id:
            continue
        markup.add(InlineKeyboardButton(goal_title, callback_data=f"goal_{goal_id}"))
    return markup

def send_goals_menu(bot, chat_id):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("➕ Добавить профиль", callback_data="add_goal"),
        InlineKeyboardButton("📋 Список профилей", callback_data="view_goals"),
        InlineKeyboardButton("🔙 Назад", callback_data="goals_back")
    )
    bot.send_message(chat_id, "🎯 Управление профилями:", reply_markup=markup)




def send_schedule_menu(bot, chat_id, message_id=None):
    """
    Меню управления расписанием автокомментинга.
    Позволяет настроить время включения и выключения автокомментинга, а также выбрать дни недели.
    """
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("➕ Установить время включения", callback_data="schedule_set_on_time"),
        InlineKeyboardButton("➖ Установить время отключения", callback_data="schedule_set_off_time"),
        InlineKeyboardButton("📅 Выбрать дни недели", callback_data="schedule_set_days"),
        InlineKeyboardButton("🗑 Удалить расписание", callback_data="schedule_delete"),
        InlineKeyboardButton("📋 Посмотреть текущее расписание", callback_data="schedule_view"),
        InlineKeyboardButton("🔙 Назад", callback_data="schedule_back")
    )
    if message_id:
        bot.edit_message_text(
            "🕒 Настроить расписание автокомментинга:",
            chat_id,
            message_id,
            reply_markup=markup
        )
    else:
        bot.send_message(
            chat_id,
            "🕒 Настроить расписание автокомментинга:",
            reply_markup=markup
        )

def send_comments_menu(bot: TeleBot, chat_id: int):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("📁 Загрузить комментарии", callback_data="upload_from_file"),
        InlineKeyboardButton("❌ Удалить комментарий", callback_data="delete_comment"),
        InlineKeyboardButton("📋 Список комментариев", callback_data="list_comments"),
        InlineKeyboardButton("🗑️ Удалить все комментарии", callback_data="clear_comments")
    )
    bot.send_message(chat_id, "💬 Выберите действие с комментариями:", reply_markup=markup)


