import re
import os
import json
import logging, random, time
from anti_spam import AntiSpamController as controller

from telebot.apihelper import ApiTelegramException


from datetime import datetime
from selenium.webdriver.support import expected_conditions as EC
from collections import defaultdict

from db import comments_file

_log_messages = defaultdict(list)  # Добавить эту строку
import asyncio


from selenium.common import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from db.settings import get_setting
import asyncio
import telebot



from utils.helpers import log_event
from telebot import TeleBot
from telebot.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from ui.menus import (
    admin_menu,
    send_settings_menu,
    send_goals_menu,
    send_schedule_menu,
    send_comments_menu
)
from db.comments1 import get_comment_stats_text, get_all_comments
from admin_utils import is_admin
from auth.inst_auth import InstaAuthManager
from core.accounts import ACCOUNTS_ROTATION, pick_account
from telebot import types
from auth.selenium_auth import SeleniumSessionManager
from db.settings import add_goal, delete_goal, get_all_goals, set_setting
from db.comments_file import (
    get_comment_stats_text,
    add_comments,
    get_random_comment, delete_comment
)

from db.settings import (
    get_all_settings,
    set_setting,
    get_target_url  # Добавьте это
)


from db.comments_file import get_random_comment, get_custom_comment
from collections import defaultdict
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import threading
import asyncio
from anti_spam import AntiSpamController
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

anti_spam = AntiSpamController(
    max_comments_per_hour=15,
    max_comments_per_day=100
)
# Файл для хранения аккаунтов
ACCOUNTS_FILE = "accounts.txt"
SETTINGS_PATH = "settings.json"
# Временное хранилище для данных на этапе ввода
_schedule_state = {}
_temp_data = {}
COMMENT_MODE = {}
monitoring_threads = {}
last_post_urls: dict[int, dict[str, str]] = defaultdict(dict)
_goals_cache: dict[int, list[str]] = defaultdict(list)
controller = AntiSpamController(max_comments_per_hour=10, max_comments_per_day=50)
_temp_data = {}
_log_messages = defaultdict(list)






if not os.path.exists(SETTINGS_PATH):
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=2)


def back_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(KeyboardButton("⬅️ Назад"))
    return kb

def load_settings() -> dict:
    if not os.path.exists(SETTINGS_PATH):
        return {}
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception) as e:
        logging.error(f"Ошибка загрузки настроек: {str(e)}")
        return {}

def save_settings(settings: dict):
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Ошибка сохранения настроек: {str(e)}")

def start_schedule_watcher():
    def watcher():
        while True:
            now = datetime.now()
            try:
                sched = load_settings().get("schedule")
                # Остальной код...
            except Exception as e:
                logging.error(f"Ошибка в watcher: {str(e)}")
                # Восстанавливаем дефолтные настройки
                with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                    json.dump({"schedule": {}}, f)
            time.sleep(60)

def get_all_settings() -> dict:
    return load_settings()



def start_schedule_watcher():
    def watcher():
        while True:
            now = datetime.now()
            sched = load_settings().get("schedule")
            if sched:
                try:
                    on_t = datetime.strptime(sched["on"], "%H:%M").time()
                    off_t = datetime.strptime(sched["off"], "%H:%M").time()
                    days = sched.get("days", [])
                    active = now.weekday() in days and on_t <= now.time() < off_t
                except Exception:
                    active = False
                # Остановить мониторинг, если не в расписании
                if not active:
                    monitoring_threads.clear()
            time.sleep(60)

    thread = threading.Thread(target=watcher, daemon=True)
    thread.start()


def register_basic_handlers(bot: TeleBot):
    start_schedule_watcher()
    @bot.message_handler(commands=["setprofile"])
    def cmd_set_profile(message: Message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(message, "❗️ Использование: /setprofile <URL профиля Instagram>")
            return

        profile_url = parts[1].strip()
        set_setting("profile_url", profile_url)
        bot.reply_to(message, f"✅ Профиль установлен: {profile_url}")

    def monitor_profiles(chat_id: int, profiles: list[str], mode: str, active_flag: threading.Event,
                         poll_interval: int = 30):
        session = pick_account()
        if not session:
            bot.send_message(chat_id, "⚠️ Нет доступных аккаунтов для мониторинга.")
            return

        # Инициализация истории постов
        for url in profiles:
            last_post_urls[chat_id].setdefault(url, None)

        try:
            # Главный цикл мониторинга с проверкой флага
            while not active_flag.is_set():
                for profile_url in profiles:
                    if active_flag.is_set():
                        break

                    try:
                        # ======= 1. Просмотр сторис ========
                        if controller.can_watch_story():
                            try:
                                if session.watch_random_story(profile_url):
                                    controller.log_story()
                                    bot.send_message(
                                        chat_id,
                                        f"📸 Просмотрена сторис @{profile_url.split('/')[-2]}",
                                        disable_notification=True
                                    )
                                    time.sleep(random.uniform(2, 5))
                            except Exception as e:
                                logging.warning(f"Ошибка просмотра сторис: {str(e)}")

                        # ======= 2. Проверка новых постов ========
                        session.driver.get(profile_url)

                        # Ожидание загрузки с проверкой флага
                        start_time = time.time()
                        while (time.time() - start_time) < 30:
                            if active_flag.is_set() or session.driver.execute_script(
                                    "return document.readyState") == "complete":
                                break
                            time.sleep(1)

                        # Проверка приватности профиля
                        try:
                            private_check = session.driver.find_element(By.XPATH,
                                                                        '//h2[contains(text(), "This Account is Private")]')
                            if private_check:
                                bot.send_message(chat_id, f"🔒 Профиль приватный: {profile_url}")
                                continue
                        except NoSuchElementException:
                            pass

                        # Поиск нового поста
                        posts = WebDriverWait(session.driver, 20).until(
                            EC.presence_of_all_elements_located((By.XPATH,
                                                                 '//a[contains(@href, "/p/")'
                                                                 ' or contains(@href, "/reel/")'
                                                                 ' or contains(@href, "/tv/")]'
                                                                 ))
                        )
                        newest_url = posts[0].get_attribute('href') if posts else None

                        if not newest_url:
                            continue

                        if last_post_urls[chat_id].get(profile_url) is None:
                            last_post_urls[chat_id][profile_url] = newest_url
                            continue

                        # ======= 3. Обработка нового поста ========
                        if newest_url != last_post_urls[chat_id].get(profile_url):
                            # Лайкинг
                            try:
                                new_posts = session.get_new_posts(profile_url)
                                if new_posts:
                                    asyncio.run(
                                        controller.random_like_posts(
                                            new_posts,
                                            like_probability=0.3,
                                            min_delay=2,
                                            max_delay=5
                                        )
                                    )
                            except Exception as e:
                                logging()

                            # Комментирование
                            if controller.can_comment():
                                controller.maybe_take_break()
                                result = session.post_comment(newest_url, comment_mode=mode)

                                if result.get("success"):
                                    controller.log_comment()
                                    bot.send_message(
                                        chat_id,
                                        f"💬 Новый комментарий: {result['comment'][:50]}...\n{newest_url}"
                                    )
                                else:
                                    logging.error(f"Ошибка коммента: {result.get('error')}")

                            last_post_urls[chat_id][profile_url] = newest_url

                        # ======= Пауза между проверками ========
                        start_time = time.time()
                        while (time.time() - start_time) < poll_interval:
                            if active_flag.is_set():
                                break
                            time.sleep(1)  # Частые проверки флага

                    except Exception as e:
                        logging.error(f"Ошибка мониторинга {profile_url}: {str(e)}")
                        bot.send_message(chat_id, f"⚠️ Временная ошибка: {str(e)[:200]}")

                    if active_flag.is_set():
                        break

                # Пауза между полными циклами проверки
                if active_flag.is_set():
                    break
                time.sleep(15)

        except Exception as e:
            logging.error(f"Критическая ошибка мониторинга: {str(e)}")
            bot.send_message(chat_id, f"🚨 Мониторинг остановлен из-за ошибки: {str(e)[:200]}")
        finally:
            logging.info(f"Мониторинг для чата {chat_id} остановлен")
            # Закрываем сессию только при ошибке, но не при штатном стопе
            if session and not active_flag.is_set():
                session.close()

    def start_monitoring_for_chat(chat_id: int, mode: str):
        if chat_id in monitoring_threads:
            bot.send_message(chat_id, "ℹ️ Мониторинг уже запущен.")
            return

        profiles = get_all_goals()
        active_flag = threading.Event()
        thread = threading.Thread(
            target=monitor_profiles,
            args=(chat_id, profiles, mode, active_flag),
            daemon=True
        )
        monitoring_threads[chat_id] = {"thread": thread, "active": active_flag}
        thread.start()
        bot.send_message(chat_id, "▶️ Мониторинг запущен.")

    @bot.message_handler(func=lambda m: m.text == "⏹️ Стоп")
    def stop_monitoring(message):
        chat_id = message.chat.id
        if chat_id in monitoring_threads:
            # Сигнализируем потоку остановиться
            monitoring_threads[chat_id]["active"].set()
            # Ожидаем завершения потока (опционально)
            monitoring_threads[chat_id]["thread"].join(timeout=5)
            # Удаляем из хранилища
            del monitoring_threads[chat_id]
            last_post_urls.pop(chat_id, None)
            bot.send_message(chat_id, "⏹️ Мониторинг остановлен.")
        else:
            bot.send_message(chat_id, "ℹ️ Мониторинг не активен.")


    @bot.message_handler(commands=['start'])
    def cmd_start(message: Message):
        if not is_admin(message.from_user.id):
            bot.send_message(message.chat.id, "⛔️ Доступ запрещён.")
            return
        bot.send_message(message.chat.id, "👋 Привет! Выбери команду:", reply_markup=admin_menu())

    @bot.message_handler(func=lambda m: m.text == "➕ Добавить аккаунт")
    def cmd_add_account(message: Message):
        log_event(f"Начало добавления аккаунта пользователем {message.from_user.id}")
        chat_id = message.chat.id
        user_id = message.from_user.id
        _temp_data[user_id] = {}

        # Только один раз отправляем сообщение + клавиатуру «Назад»
        bot.send_message(
            chat_id,
            "🆕 Введите логин нового аккаунта:",
            reply_markup=back_keyboard()
        )
        bot.register_next_step_handler(message, process_username)

    @bot.message_handler(commands=['seturl'])
    def cmd_seturl(message: types.Message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            return bot.reply_to(message, "❗️ Использование: /seturl <URL>")
        url = args[1].strip()
        from db.settings import set_setting
        set_setting("target_url", url)
        bot.reply_to(message, f"✅ Сохранён target_url = {url}")
        log_event(f"Установлен target_url = {url}")



    @bot.callback_query_handler(func=lambda call: call.data == "upload_from_file")
    def callback_upload_from_file(call: CallbackQuery):
        msg = bot.send_message(
            call.message.chat.id,
            "📤 Отправьте TXT файл с комментариями (каждый комментарий с новой строки)"
        )
        bot.register_next_step_handler(msg, process_comments_file)

    @bot.callback_query_handler(
        func=lambda c: c.data in ['upload_from_file', 'delete_comment', 'list_comments', 'clear_comments'])
    def callback_comments(call: CallbackQuery):
        chat_id = call.message.chat.id
        data = call.data
        bot.answer_callback_query(call.id)

        if data == 'upload_from_file':
            bot.send_message(chat_id, '❗ Пришлите мне файл с комментариями для загрузки.')
        elif data == 'delete_comment':
            bot.send_message(chat_id, '❗ Введите команду для удаления: /delete_comment <текст комментария>')
        elif data == 'list_comments':
            comments = comments_file.get_all_comments()
            if comments:
                header = "📋 Список комментариев:\n"
                body = "\n".join(f"- {c}" for c in comments)
                text = header + body
            else:
                text = 'Список комментариев пуст.'
            bot.send_message(chat_id, text)
        elif data == 'clear_comments':
            success = comments_file.delete_all_comments()
            if success:
                bot.send_message(chat_id, '✅ Все комментарии удалены.')
            else:
                bot.send_message(chat_id, '⚠️ Не удалось удалить комментарии или база пуста.')

    # Команда удаления комментария
    @bot.message_handler(commands=['delete_comment'])
    def handle_delete_comment(message: Message):
        args = message.text.split(None, 1)
        if len(args) < 2 or not args[1].strip():
            bot.reply_to(message, '❗ Использование: /delete_comment <текст комментария>')
            return
        comment_to_delete = args[1].strip()
        success = comments_file.delete_comment(comment_to_delete)
        if success:
            bot.reply_to(message, f'✅ Комментарий удален: "{comment_to_delete}"')
        else:
            bot.reply_to(message, f'⚠️ Комментарий не найден: "{comment_to_delete}"')

    # Команда просмотра списка
    @bot.message_handler(commands=['list_comments'])
    def handle_list_comments(message: Message):
        comments = comments_file.get_all_comments()
        if comments:
            header = "📋 Список комментариев:\n"
            body = "\n".join(f"- {c}" for c in comments)
            text = header + body
        else:
            text = 'Список комментариев пуст.'
        bot.reply_to(message, text)

    def process_comments_file(message: Message):
        if not message.document:
            bot.reply_to(message, "❌ Нужно отправить файл в формате TXT")
            return

        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        try:
            comments = downloaded_file.decode('utf-8').splitlines()
            valid_comments = [c.strip() for c in comments if 10 <= len(c.strip()) <= 300]

            add_comments(valid_comments)

            bot.reply_to(
                message,
                f"✅ Загружено {len(valid_comments)} комментариев\n"
                f"❌ Отклонено: {len(comments) - len(valid_comments)}"
            )
        except Exception as e:
            bot.reply_to(message, f"❌ Ошибка обработки файла: {str(e)}")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("select_goal:"))
    def callback_select_goal(call: CallbackQuery):
        chat_id = call.message.chat.id
        idx = int(call.data.split(":", 1)[1])
        goals = get_all_goals()  # Получаем актуальный список из БД

        if 0 <= idx < len(goals):
            profile_url = goals[idx]
            set_setting("profile_url", profile_url)  # Сохраняем профиль
            bot.answer_callback_query(call.id, f"✅ Профиль выбран: {profile_url}")
            log_event(f"Выбран профиль: {profile_url}")
        else:
            bot.answer_callback_query(call.id, "❌ Профиль не найден")
            send_goals_menu(bot, chat_id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("delete_goal:"))
    def callback_delete_goal(call: CallbackQuery):
        chat_id = call.message.chat.id
        msg_id = call.message.message_id

        # Снова загрузим актуальный список и кешируем
        goals = get_goals(chat_id)

        idx = int(call.data.split(":", 1)[1])
        if idx < 0 or idx >= len(goals):
            bot.answer_callback_query(call.id, "❌ Цель не найдена, обновите список.")
            # отредактировать меню, убрав старые кнопки
            send_goals_menu(bot, chat_id, msg_id)
            return

        url = goals[idx]
        deleted = delete_goal(url)
        log_event(f"delete_goal: удалено строк = {deleted} для URL {url}", level='info')

        # Обновляем кеш и клавиатуру в том же сообщении
        get_goals(chat_id)  # заново прочитает из БД и обновит _goals_cache
        send_goals_menu(bot, chat_id, msg_id)

        bot.answer_callback_query(call.id, f"✅ Цель удалена: {url}")

    @bot.callback_query_handler(func=lambda call: call.data == "settings_back")
    def callback_settings_back(call: CallbackQuery):
        bot.answer_callback_query(call.id)
        # удаляем старое inline-меню
        bot.delete_message(call.message.chat.id, call.message.message_id)
        # шлём новое сообщение с основной клавиатурой
        bot.send_message(call.message.chat.id, "👋 Главное меню. Выбери команду:", reply_markup=admin_menu())


    @bot.callback_query_handler(func=lambda call: call.data == "goals_back")
    def callback_goals_back(call: CallbackQuery):
        bot.edit_message_text(
            "👋 Главное меню. Выбери команду:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=admin_menu()
        )
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data == "schedule_back")
    def callback_schedule_back(call: CallbackQuery):
        bot.answer_callback_query(call.id)
        # удаляем текущее сообщение с inline-кнопками
        bot.delete_message(call.message.chat.id, call.message.message_id)
        # отправляем новое с обычной клавиатурой
        bot.send_message(call.message.chat.id, "👋 Главное меню. Выбери команду:", reply_markup=admin_menu())

    @bot.callback_query_handler(func=lambda call: call.data.startswith("schedule_"))
    def callback_schedule(call: CallbackQuery):
        bot.answer_callback_query(call.id)
        data = call.data
        if data == "schedule_set_on_time":
            msg = bot.send_message(call.message.chat.id, "⏰ Введите время включения (HH:MM):")
            bot.register_next_step_handler(msg, process_schedule_on_time)
        elif data == "schedule_set_off_time":
            msg = bot.send_message(call.message.chat.id, "⏰ Введите время отключения (HH:MM):")
            bot.register_next_step_handler(msg, process_schedule_off_time)
        elif data == "schedule_set_days":
            days_markup = InlineKeyboardMarkup(row_width=3)
            labels = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]
            for idx, lbl in enumerate(labels):
                days_markup.add(InlineKeyboardButton(lbl, callback_data=f"schedule_day_{idx}"))
            days_markup.add(InlineKeyboardButton("✅ Готово", callback_data="schedule_days_done"))
            bot.send_message(call.message.chat.id, "📅 Выберите дни:", reply_markup=days_markup)

        elif data.startswith("schedule_day_"):
            cid = call.message.chat.id
            idx = int(data.split("_")[-1])
            sel = _schedule_state.setdefault(cid, {"days": set(), "on": None, "off": None})
            if idx in sel["days"]:
                sel["days"].remove(idx)
            else:
                sel["days"].add(idx)
            # Вместо рекурсии — просто обновляем меню дней:
            days_markup = InlineKeyboardMarkup(row_width=3)
            labels = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]
            for i, lbl in enumerate(labels):
                prefix = "✅ " if i in sel["days"] else ""
                days_markup.add(InlineKeyboardButton(prefix + lbl, callback_data=f"schedule_day_{i}"))
            days_markup.add(InlineKeyboardButton("✅ Готово", callback_data="schedule_days_done"))
            bot.edit_message_reply_markup(chat_id=cid,
                                          message_id=call.message.message_id,
                                          reply_markup=days_markup)

        elif data == "schedule_days_done":
            cid = call.message.chat.id
            state = _schedule_state.get(cid, {})
            settings = load_settings()
            settings.setdefault("schedule", {})["days"] = sorted(state.get("days", []))
            save_settings(settings)
            bot.send_message(cid, f"✅ Дни сохранены: {settings['schedule']['days']}")
            send_schedule_menu(bot, cid)
        elif data == "schedule_view":
            sched = load_settings().get("schedule", {})
            bot.send_message(call.message.chat.id,
                             f"🕒 Расписание:\nВкл: {sched.get('on')}\nВыкл: {sched.get('off')}\nДни: {sched.get('days')}")
        elif data == "schedule_delete":
            settings = load_settings()
            settings.pop("schedule", None)
            save_settings(settings)
            bot.send_message(call.message.chat.id, "✅ Расписание удалено")
            send_schedule_menu(bot, call.message.chat.id)
        elif data == "schedule_back":
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(call.message.chat.id, "👋 Главное меню. Выбери команду:", reply_markup=admin_menu())

    # ──────────────── Обработчики ввода времени ────────────────

    def process_schedule_on_time(message: Message):
        t = message.text.strip()
        settings = load_settings()
        settings.setdefault("schedule", {})["on"] = t
        save_settings(settings)
        bot.reply_to(message, f"✅ Время включения установлено: {t}")
        send_schedule_menu(bot, message.chat.id)

    def process_schedule_off_time(message: Message):
        t = message.text.strip()
        settings = load_settings()
        settings.setdefault("schedule", {})["off"] = t
        save_settings(settings)
        bot.reply_to(message, f"✅ Время отключения установлено: {t}")
        send_schedule_menu(bot, message.chat.id)

    @bot.callback_query_handler(func=lambda call: call.data == "add_goal")
    def callback_add_goal(call: CallbackQuery):
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "📥 Введите новую ссылку цели:")
        bot.register_next_step_handler(msg, process_new_goal)

    def process_new_goal(message: Message):
        url = message.text.strip().lower()

        # Проверка формата профиля Instagram
        if not re.match(r'^(https?:\/\/)?(www\.)?instagram\.com\/[a-zA-Z0-9_.]+\/?$', url):
            bot.send_message(message.chat.id, "❌ Некорректный URL профиля. Пример: https://www.instagram.com/username/")
            return

        # Сохраняем в настройках как профиль
        set_setting("profile_url", url)
        add_goal(url)  # Сохраняем в таблице goals
        log_event(f"Добавлен профиль: {url}", level='info')
        bot.send_message(message.chat.id, f"✅ Профиль добавлен:\n{url}")
        send_goals_menu(bot, message.chat.id)

    @bot.message_handler(commands=['comment'])
    def handle_comment(message: types.Message):
        log_event(f"Комментирование запрошено пользователем {message.from_user.id}")
        bot.reply_to(message, "▶️ Запускаю автокомментинг…")

        settings = get_all_settings()
        target_url = settings.get("target_url")
        if not target_url:
            bot.reply_to(message, "❌ URL поста не найден в настройках.")
            log_event("Ошибка: target_url не задан в настройках", level='error')
            return

        session = pick_account()
        if not session:
            bot.reply_to(message, "⚠️ Нет доступных аккаунтов.")
            log_event("Нет доступных аккаунтов для комментариев", level='warning')
            return

        # ─── Антиспам-проверки ────────────────────────────────────────────────────
        if not controller.can_comment():
            return bot.reply_to(message, "🚫 Пропускаю: исчерпаны лимиты или бот на перерыве.")


        controller.maybe_take_break()



        result = session.post_comment(target_url)

        if result.get("success"):

            controller.log_comment()
            bot.reply_to(message, f"✅ Отправил комментарий: «{result['comment']}»")
            log_event(f"Комментарий отправлен: {result['comment']}")
        else:
            reason = result.get('reason') or result.get('error', '').splitlines()[-1]
            bot.reply_to(message, f"❌ Не удалось: {reason}")
            log_event(f"Ошибка при отправке комментария: {reason}", level='error')





    def process_username(message: Message):
        text = message.text.strip()
        # 1) Обработка «Назад»
        if text == "⬅️ Назад":
            _temp_data.pop(message.from_user.id, None)
            # сбросить любой pending-step handler
            bot.clear_step_handler_by_chat_id(message.chat.id)
            # показать главное меню
            bot.send_message(
                message.chat.id,
                "👋 Возвращаемся в главное меню. Выбери команду:",
                reply_markup=admin_menu()
            )
            return

        # 2) Если не «Назад» — обычная логика
        user_id = message.from_user.id
        _temp_data[user_id]['username'] = text
        bot.send_message(
            message.chat.id,
            "🔑 Введите пароль для аккаунта:",
            reply_markup=back_keyboard()
        )
        bot.register_next_step_handler(message, process_password)
        log_event(f"Пользователь {user_id} ввёл логин: {text}")

    def process_password(message: Message):
        text = message.text.strip()
        if text == "⬅️ Назад":
            _temp_data.pop(message.from_user.id, None)
            bot.clear_step_handler_by_chat_id(message.chat.id)
            bot.send_message(
                message.chat.id,
                "👋 Возвращаемся в главное меню. Выбери команду:",
                reply_markup=admin_menu()
            )
            return

        user_id = message.from_user.id
        _temp_data[user_id]['password'] = text
        bot.send_message(
            message.chat.id,
            "🛡 Если используется прокси, введите его, иначе напишите 'нет' для пропуска:"

        )
        bot.register_next_step_handler(message, process_proxy)
        log_event(f"Пользователь {user_id} ввёл пароль")

    def process_proxy(message: Message):
        user_id = message.from_user.id
        text = message.text.strip()
        proxy = None if not text or text.lower() in ('нет', 'no', '-') else text
        _temp_data[user_id]['proxy'] = proxy
        data = _temp_data[user_id]

        bot.send_message(message.chat.id, "⏳ Пытаемся авторизоваться через InstaAuthManager...")
        log_event(f"Пользователь {user_id} ввёл прокси: {proxy if proxy else 'без прокси'}")
        auth_manager = InstaAuthManager(data['username'], data['password'], data['proxy'])
        data['auth_manager'] = auth_manager
        result = auth_manager.login()

        if not result or not isinstance(result, dict):
            bot.send_message(message.chat.id, "❌ Не удалось авторизоваться: неизвестная ошибка.")
            _temp_data.pop(user_id, None)
            return

        error = result.get('error', '')
        error_lower = error.lower() if isinstance(error, str) else ''

        if result.get('2fa_required'):
            bot.send_message(
                message.chat.id,
                "🔐 Требуется подтверждение входа или код 2FA. Введите код из приложения/смс или подтвердите вход через Instagram:"
            )
            bot.register_next_step_handler(message, process_2fa)
            return

        if result.get('challenge_required'):
            bot.send_message(
                message.chat.id,
                "📧 Instagram отправил код подтверждения на email. Введите его (возможно 3-значный):"
            )
            bot.register_next_step_handler(message, process_challenge_code)
            return

        if 'blacklist' in error_lower or 'email' in error_lower:
            bot.send_message(
                message.chat.id,
                "❌ Не удалось авторизовать аккаунт: IP заблокирован или требуется восстановление через email."
            )
            _temp_data.pop(user_id, None)
            return

        if not result.get('success'):
            bot.send_message(
                message.chat.id,
                f"❌ Ошибка входа: {error.strip() or 'неизвестная ошибка'}"
            )
            _temp_data.pop(user_id, None)
            return

        try:
            session = SeleniumSessionManager(data['username'], data['password'], data['proxy'])
            session.login()
            ACCOUNTS_ROTATION.append(session)
            msg = f"✅ Аккаунт @{data['username']} успешно добавлен и авторизован!"
        except Exception as e:
            msg_str = str(e)
            if '2FA or login failed' in msg_str:
                ACCOUNTS_ROTATION.append(session)
                msg = f"⚠️ Аккаунт @{data['username']} добавлен, но Selenium-сессия требует ручного входа при первом использовании."
            else:
                msg = f"❌ Не удалось создать сессию Selenium: {e}"

        line = f"{data['username']}:{data['password']}"
        if data['proxy']:
            line += f":{data['proxy']}"
        with open(ACCOUNTS_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")

        bot.send_message(message.chat.id, msg)
        _temp_data.pop(user_id, None)

    def get_goals(chat_id: int) -> list[str]:
        """Загружает из БД и кеширует для чата."""
        goals = get_all_goals()
        _goals_cache[chat_id] = goals
        return goals

    def create_goal_buttons(chat_id: int) -> InlineKeyboardMarkup:
        markup = InlineKeyboardMarkup()
        goals = get_all_goals()  # Получаем напрямую из БД

        for idx, url in enumerate(goals):
            username = url.split("/")[-1].strip("/") if "/" in url else url
            markup.row(
                InlineKeyboardButton(
                    f"👤 {username}",
                    callback_data=f"select_goal:{idx}"
                ),
                InlineKeyboardButton("❌", callback_data=f"delete_goal:{idx}")
            )
        markup.add(InlineKeyboardButton("➕ Добавить профиль", callback_data="add_goal"))
        return markup

    def send_goals_menu(bot: TeleBot, chat_id: int, message_id: int = None):
        goals = get_all_goals()  # Обновляем данные перед отображением
        text = "🎯 Список профилей:" if goals else "🎯 Список профилей пуст."
        markup = create_goal_buttons(chat_id)

        if message_id:
            bot.edit_message_text(
                text,
                chat_id,
                message_id,
                reply_markup=markup
            )
        else:
            bot.send_message(
                chat_id,
                text,
                reply_markup=markup
            )

    def process_2fa(message: Message):
        user_id = message.from_user.id
        code = message.text.strip()
        data = _temp_data.get(user_id)
        if not data:
            bot.send_message(message.chat.id, "❌ Сессия авторизации не найдена. Повторите добавление.")
            log_event(f"Ошибка: нет данных сессии для 2FA пользователя {user_id}", level='error')
            return

        auth_manager = data.get('auth_manager')
        if not auth_manager:
            bot.send_message(message.chat.id, "❌ Сессия 2FA не найдена. Повторите добавление аккаунта.")
            log_event(f"Ошибка: нет данных сессии для 2FA пользователя {user_id}", level='error')
            return

        result = auth_manager.submit_2fa(code)

        if not result or not isinstance(result, dict):
            bot.send_message(message.chat.id, "❌ Не удалось обработать код 2FA. Попробуйте снова.")
            log_event(f"Ошибка обработки кода 2FA для пользователя {user_id}", level='error')
            _temp_data.pop(user_id, None)
            return

        if not result.get('success'):
            bot.send_message(
                message.chat.id,
                f"❌ Неверный код или ошибка: {result.get('error').strip() or 'unknown'}"
            )
            log_event(f"Неверный код 2FA для пользователя {user_id}", level='warning')
            _temp_data.pop(user_id, None)
            return
        log_event(f"2FA успешно пройден для пользователя {user_id}")

        # Теперь добавляем сессию Selenium после успешного входа
        try:
            # Создание сессии Selenium
            session = SeleniumSessionManager(data['username'], data['password'], data['proxy'])
            if session.login():  # Используем login() для авторизации
                ACCOUNTS_ROTATION.append(session)
                msg = f"✅ Аккаунт @{data['username']} успешно добавлен и авторизован!"
            else:
                msg = f"❌ Не удалось создать сессию Selenium для аккаунта @{data['username']}."
        except Exception as e:
            msg = f"❌ Не удалось создать сессию Selenium: {e}"

        # Записываем аккаунт в файл
        line = f"{data['username']}:{data['password']}"
        if data['proxy']:
            line += f":{data['proxy']}"
        with open(ACCOUNTS_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")

        bot.send_message(message.chat.id, msg)
        _temp_data.pop(user_id, None)

    @bot.callback_query_handler(func=lambda call: call.data == "delete_logs")
    def callback_delete_logs(call: CallbackQuery):
        try:
            if os.path.exists("logs.txt"):
                os.remove("logs.txt")
                bot.answer_callback_query(call.id, "✅ Логи успешно удалены!")
                bot.edit_message_reply_markup(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=None
                )
            else:
                bot.answer_callback_query(call.id, "⚠️ Файл логов не найден")
        except Exception as e:
            logging.error(f"Ошибка удаления логов: {e}")
            bot.answer_callback_query(call.id, "❌ Ошибка при удалении логов")

    @bot.message_handler(func=lambda m: m.text == "▶️ Старт")
    def cmd_start_commenting(message: Message):
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("🎲 Рандомные", callback_data="comment_mode_random"),
            InlineKeyboardButton("📂 Из файла", callback_data="comment_mode_custom")
        )
        bot.send_message(
            message.chat.id,
            "🔘 Выберите тип комментариев:",
            reply_markup=markup
        )

    # Обработчик кнопки «Старт» (выбора режима комментирования)
    @bot.callback_query_handler(func=lambda call: call.data.startswith("comment_mode_"))
    def set_comment_mode(call: CallbackQuery):
        chat_id = call.message.chat.id
        mode = call.data.split("_")[-1]  # 'random' или 'custom'
        COMMENT_MODE[chat_id] = mode

        # Уведомляем пользователя
        friendly = "Из файла" if mode == "custom" else "Рандомные"
        bot.answer_callback_query(call.id, f"✅ Режим установлен: {friendly}")

        # Убираем кнопки
        try:
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
        except Exception:
            pass

        start_monitoring_for_chat(chat_id, mode)


    @bot.message_handler(func=lambda m: m.text == "⚙️ Настройки")
    def cmd_settings(message: Message):
        settings = get_all_settings()
        send_settings_menu(bot, message.chat.id, settings)
        log_event(f"Пользователь {message.from_user.id} открыл настройки")

    @bot.callback_query_handler(func=lambda call: call.data == "view_comments")
    def callback_view_comments(call: CallbackQuery):
        comments = get_all_comments()
        text = "\n".join(f"{i+1}. {c}" for i, c in enumerate(comments)) or "Комментариев ещё нет."
        bot.send_message(call.message.chat.id, text)
        log_event("Просмотр комментариев")

    @bot.callback_query_handler(func=lambda call: call.data == "view_logs")
    def callback_view_logs(call: CallbackQuery):
        path = "logs.txt"
        if not os.path.exists(path):
            return bot.send_message(call.message.chat.id, "Файл логов не найден.")
        with open(path, "r", encoding="utf-8") as f:
            data = f.read() or "Логи пустые."
        for i in range(0, len(data), 4000):
            bot.send_message(call.message.chat.id, f"<code>{data[i:i+4000]}</code>", parse_mode="HTML")
        log_event("Просмотр логов")

    @bot.callback_query_handler(func=lambda call: call.data == "view_stats")
    def callback_view_stats(call: CallbackQuery):
        stats = get_comment_stats_text()
        bot.send_message(call.message.chat.id, stats)
        log_event("Просмотр статистики комментариев")

    @bot.message_handler(func=lambda m: m.text == "⬅️ Назад")
    def go_back_to_menu(message: Message):
        user_id = message.from_user.id
        # очищаем накопленные данные, чтобы не мешались при повторном входе
        _temp_data.pop(user_id, None)
        bot.send_message(
            message.chat.id,
            "👋 Возвращаемся в главное меню. Выбери команду:",
            reply_markup=admin_menu()
        )

    @bot.message_handler(func=lambda m: m.text == "📊 Статистика")
    def cmd_stats(message: Message):
        stats_text = get_comment_stats_text()
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔄 Обнулить статистику", callback_data="reset_stats"))
        bot.send_message(message.chat.id, stats_text, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data == "reset_stats")
    def callback_reset_stats(call: CallbackQuery):
        try:
            if os.path.exists("comment_log.csv"):
                os.remove("comment_log.csv")
                # Обновляем сообщение
                bot.edit_message_text(
                    "📊 Статистика обнулена!",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=None
                )
            else:
                bot.answer_callback_query(call.id, "⚠️ Статистика уже пуста")
        except Exception as e:
            logging.error(f"Ошибка сброса статистики: {str(e)}")
            bot.answer_callback_query(call.id, "❌ Ошибка при обнулении")

    @bot.message_handler(func=lambda m: m.text == "🎯 Управление целями")
    def cmd_goals(message: Message):
        send_goals_menu(bot, message.chat.id)
        log_event(f"Пользователь {message.from_user.id} открыл управление целями")

    @bot.message_handler(func=lambda m: m.text == "🕒 Настроить расписание")
    def cmd_schedule(message: Message):
        send_schedule_menu(bot, message.chat.id)
        log_event(f"Пользователь {message.from_user.id} открыл меню расписания")

    @bot.message_handler(func=lambda m: m.text == "📥 Управление комментариями")
    def cmd_upload_comments(message: Message):
        send_comments_menu(bot, message.chat.id)
        log_event(f"Пользователь {message.from_user.id} открыл меню управления комментариями")

    # Добавьте глобальный словарь для хранения ID логов
    _log_messages = defaultdict(list)

    @bot.message_handler(func=lambda m: m.text == "📜 Логи")
    def cmd_logs(message: Message):
        chat_id = message.chat.id
        path = "logs.txt"

        _log_messages[chat_id].clear()

        if not os.path.exists(path):
            return bot.send_message(chat_id, "Файл логов не найден.")

        with open(path, "r", encoding="utf-8") as f:
            log_text = f.read()

        if not log_text.strip():
            return bot.send_message(chat_id, "Логи пустые.")

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🗑️ Удалить ВСЕ логи", callback_data="delete_all_logs"))

        max_length = 4000
        messages = []
        for i in range(0, len(log_text), max_length):
            chunk = log_text[i:i + max_length]
            msg = bot.send_message(chat_id, f"<code>{chunk}</code>", parse_mode="HTML")
            messages.append(msg.message_id)

        if messages:
            bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=messages[-1],
                reply_markup=markup
            )

        _log_messages[chat_id] = messages

    @bot.callback_query_handler(func=lambda call: call.data == "delete_all_logs")
    def callback_delete_all_logs(call: CallbackQuery):
        chat_id = call.message.chat.id
        try:
            # Удаление файла логов
            if os.path.exists("logs.txt"):
                os.remove("logs.txt")

            # Удаление сообщений с логами
            for msg_id in _log_messages.get(chat_id, []):
                try:
                    bot.delete_message(chat_id, msg_id)
                except Exception as e:
                    if "message to delete not found" not in str(e):
                        logging.error(f"Ошибка удаления: {str(e)}")

            # Удаление кнопки только если сообщение существует
            try:
                bot.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=call.message.message_id,
                    reply_markup=None
                )
            except Exception as e:
                if "message to edit not found" not in str(e):
                    logging.error(f"Ошибка редактирования: {str(e)}")

            _log_messages[chat_id] = []
            bot.answer_callback_query(call.id, "✅ Все логи удалены", show_alert=True)

        except Exception as e:
            logging.error(f"Ошибка удаления: {str(e)}")
            bot.answer_callback_query(call.id, "❌ Ошибка удаления", show_alert=True)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("edit_setting:"))
    def callback_edit_setting(call: CallbackQuery):
        setting_name = call.data.split(":", 1)[1]
        bot.send_message(call.message.chat.id, f"✏️ Введи новое значение для {setting_name}:")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("add_goal"))
    def callback_add_goal(call: CallbackQuery):
        bot.send_message(call.message.chat.id, "🎯 Введи новый username для цели:")

    @bot.callback_query_handler(func=lambda call: True)
    def fallback_callback(call: CallbackQuery):
        bot.answer_callback_query(call.id, "Функция в разработке.")
        log_event(f"Необработанный callback: {call.data}", level='warning')

    def process_challenge_code(message: Message):
        user_id = message.from_user.id
        code = message.text.strip()
        data = _temp_data.get(user_id)
        if not data:
            bot.send_message(message.chat.id, "❌ Данные сессии не найдены. Повторите добавление аккаунта.")
            log_event(f"Ошибка: нет данных для challenge кода пользователя {user_id}", level='error')
            return

        auth_manager = InstaAuthManager(data['username'], data['password'], data['proxy'])
        success = auth_manager.challenge_resolve(code)

        if not success:
            bot.send_message(message.chat.id, "❌ Код неверный или не удалось завершить challenge.")
            log_event(f"Ошибка при вводе challenge кода пользователем {user_id}", level='error')
            _temp_data.pop(user_id, None)
            return
        log_event(f"Challenge успешно пройден пользователем {user_id}")

        result = auth_manager.login()
        if result.get('success'):
            try:
                session = SeleniumSessionManager(data['username'], data['password'], data['proxy'])
                session.login()
                ACCOUNTS_ROTATION.append(session)
                msg = f"✅ Аккаунт @{data['username']} успешно авторизован после challenge!"
            except Exception as e:
                msg = f"⚠️ Авторизация прошла, но Selenium не запущен: {e}"
        else:
            msg = f"❌ Не удалось авторизовать аккаунт после ввода кода: {result.get('error')}"

        line = f"{data['username']}:{data['password']}"
        if data['proxy']:
            line += f":{data['proxy']}"
        with open(ACCOUNTS_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")

        bot.send_message(message.chat.id, msg)
        _temp_data.pop(user_id, None)










