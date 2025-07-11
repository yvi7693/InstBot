import os
import pickle
import time
import logging
import traceback
import random
import undetected_chromedriver as uc
from selenium.webdriver import ActionChains


import time
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, \
    StaleElementReferenceException
from datetime import datetime

import undetected_chromedriver as uc
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, NoSuchElementException
from telebot import types
from core.comments import random_template_comment, is_within_commenting_hours
from db.comments1 import log_comment_stat
from db.comments_file import get_random_comment

COOKIES_DIR = os.path.join(os.path.dirname(__file__), '..', 'sessions')
os.makedirs(COOKIES_DIR, exist_ok=True)
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
from db.comments_file import get_random_comment
from db.comments_file import get_custom_comment
from core.comments import random_template_comment


def human_pause(a=0.5, b=3.0):
    """Пауза между действиями для имитации человека."""
    time.sleep(random.uniform(a, b))

def click_element(driver, element):
    actions = ActionChains(driver)
    actions.move_to_element(element)
    actions.pause(random.uniform(0.5, 2.0))
    actions.click()
    actions.perform()


class InstagramPost:
    def __init__(self, url: str, driver):
        self.url = url
        self.driver = driver
        self.id = url.split("/")[-2] if "/" in url else "unknown"

    async def like(self):
        """Ставит лайк на пост с улучшенной обработкой"""
        try:
            self.driver.get(self.url)

            # Ожидаем полной загрузки страницы
            WebDriverWait(self.driver, 15).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )

            # Новая стратегия поиска кнопки лайка
            like_btn = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'svg[aria-label="Нравится"]')
                )
            )

            # Кликаем через Actions API
            actions = webdriver.ActionChains(self.driver)
            actions.move_to_element(like_btn).click().perform()

            # Добавляем человеческую задержку
            time.sleep(random.uniform(1.5, 3.5))
            logging.info(f"❤️ Успешный лайк на пост {self.id}")

        except Exception as e:
            logging.error(f"Ошибка лайка {self.id}: {str(e)}")
            raise

class SeleniumSessionManager:
    def __init__(self, username: str, password: str, proxy: str = None):
        self.username = username
        self.password = password
        self.proxy = proxy
        self.driver = None  # Сюда будет сохраняться экземпляр драйвера

    def login(self):
        options = uc.ChromeOptions()
        if self.proxy:
            options.add_argument(f'--proxy-server={self.proxy}')

        self.driver = uc.Chrome(options=options, headless=False)

        # Переходим на страницу входа
        self.driver.get("https://www.instagram.com/accounts/login/")

        time.sleep(2)  # Ждем загрузки страницы

        # Находим поля ввода и кнопку входа
        username_input = self.driver.find_element(By.NAME, "username")
        password_input = self.driver.find_element(By.NAME, "password")
        login_button = self.driver.find_element(By.XPATH, '//button[@type="submit"]')

        # Вводим данные и нажимаем кнопку входа
        username_input.send_keys(self.username)
        password_input.send_keys(self.password)
        click_element(self.driver, login_button)

        # Ожидаем немного для загрузки
        time.sleep(5)

        # Проверка на успешный вход (можно добавить более сложную проверку)
        if "instagram" in self.driver.current_url:
            print(f"✅ Успешный вход для {self.username}")
            return True
        else:
            print(f"❌ Не удалось войти в аккаунт {self.username}")
            return False

    def close(self):
        """Закрыть сессию Selenium."""
        if self.driver:
            self.driver.quit()

    def _ensure_login(self):
        cookies = self._load_cookies_file()
        if not cookies:
            logging.info("🔄 No existing cookies, performing web login...")
            self._perform_web_login()  # Без передачи аргументов (заменим позже)
        else:
            if not self._try_login_with_cookies(cookies):
                logging.warning("⚠️ Cookies invalid, re-login through form...")
                self._perform_web_login()  # Без передачи аргументов (заменим позже)

    def _load_cookies_file(self):
        if os.path.exists(self.cookies_path):
            with open(self.cookies_path, 'rb') as f:
                data = pickle.load(f)
            logging.debug(f"🔍 Loaded {len(data)} cookies from file")
            return data
        return []

    def _save_cookies_file(self, cookies):
        with open(self.cookies_path, 'wb') as f:
            pickle.dump(cookies, f)
        logging.info(f"💾 Saved {len(cookies)} cookies to {self.cookies_path}")

    def _try_login_with_cookies(self, cookies) -> bool:
        try:
            self.driver.get('https://www.instagram.com/')
            for c in cookies:
                if 'name' in c and 'value' in c:
                    self.driver.add_cookie(c)
            self.driver.refresh()
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, 'nav'))
            )
            logging.info("✅ Logged in via cookies")
            return True
        except Exception as e:
            logging.debug(f"Cookie login failed: {e}")
            return False

    def _perform_web_login(self, bot=None, message=None):  # Добавлены параметры
        self.driver.get('https://www.instagram.com/accounts/login/?hl=en')

        try:
            # Ждем загрузки страницы
            WebDriverWait(self.driver, 15).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )

            # Сохраняем страницу для дебага
            self.driver.save_screenshot("login_debug.png")
            with open("login_debug.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)

            # Вводим логин и пароль
            username_input = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.NAME, 'username'))
            )
            username_input.send_keys(self.username)

            password_input = self.driver.find_element(By.NAME, 'password')
            password_input.send_keys(self.password)

            login_btn = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            try:
                click_element(self.driver, login_btn)
            except ElementClickInterceptedException:
                self.driver.execute_script("arguments[0].click();", login_btn)

            # Пытаемся нажать "Not Now" на сохранение логина
            try:
                not_now_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Not Now')]"))
                )
                click_element(self.driver, not_now_btn)
                logging.info("ℹ️ Нажали 'Not Now' на 'Save Your Login Info?'")
            except Exception:
                logging.debug("❔ 'Save Login Info' окно не появилось")

            # Пытаемся нажать "Not Now" на уведомления
            try:
                not_now_notifications_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Not Now')]"))
                )
                click_element(self.driver, not_now_notifications_btn)
                logging.info("ℹ️ Нажали 'Not Now' на 'Turn on Notifications'")

            except Exception:
                logging.debug("❔ 'Turn on Notifications' окно не появилось")

            # Проверяем URL, чтобы убедиться, что мы не на странице 2FA
            if "two_factor" in self.driver.current_url:
                logging.error("⚠️ Требуется 2FA для аккаунта.")

                # Отправляем запрос на ввод 2FA кода в Telegram
                if bot and message:  # Проверяем, переданы ли параметры
                    bot.send_message(message.chat.id, "⚠️ Требуется код двухфакторной аутентификации (2FA). Пожалуйста, введите код.")

                # Ожидаем код от пользователя
                if bot and message:
                    bot.register_next_step_handler(message, self.handle_2fa_code, bot)
                return  # Прерываем выполнение, чтобы дождаться ввода кода 2FA

            # Проверка на успешный вход (если нужна дополнительная проверка)
            if self._wait_for_login_success():
                # Сохраняем куки после входа
                new_cookies = self.driver.get_cookies()
                self._save_cookies_file(new_cookies)
                logging.info("✅ Web login successful and cookies updated")
            else:
                raise Exception("Не удалось подтвердить успешный вход после логина.")

        except Exception as e:
            self.driver.save_screenshot("login_error.png")
            logging.error(f"❌ Web login error: {traceback.format_exc()}")
            raise

    def _generate_comment(self, mode: str) -> str:
        """Генерация комментария с проверкой"""
        logging.info(f"Режим комментирования: {mode}")

        if mode == 'custom':
            comment = get_custom_comment()
            if comment:
                return comment
            logging.warning("Нет кастомных комментариев, использую рандомные")

        return random_template_comment()

    def post_comment(self, post_url: str, comment_mode: str = 'random'):
        """
        Открывает пост по URL и отправляет комментарий.
        comment_mode: 'random' — только из шаблонов random_template_comment()
                      'custom' — только из файла get_custom_comment()
        """

        # 1) Выбираем текст комментария по режиму
        if comment_mode == 'custom':
            text = get_custom_comment()
            if not text:
                # Если файл пуст или комментариев больше нет — fallback на рандом
                text = random_template_comment()
        else:
            text = random_template_comment()

        # 2) Открываем страницу поста
        self.driver.get(post_url)
        time.sleep(2)  # ждём загрузки

        # 3) Проверяем, можно ли сейчас комментировать
        if not is_within_commenting_hours():
            logging.info("⏰ Вне допустимого времени для комментирования.")
            return {"success": False, "reason": "outside_hours"}

        try:
            # 4) Нажимаем на иконку «Комментировать»
            comment_icon = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'svg[aria-label="Комментировать"]'))
            )
            click_element(self.driver, comment_icon)
            time.sleep(1.5)  # ждём появления поля ввода

            # 5) Находим поле ввода и вставляем текст
            for _ in range(3):
                try:
                    field = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[contenteditable="true"], textarea'))
                    )
                    click_element(self.driver, field)
                    # Вставка через JS, чтобы обойти React-проблемы
                    self.driver.execute_script("""
                        const elm = arguments[0], txt = arguments[1];
                        elm.focus();
                        document.execCommand('selectAll', false, null);
                        document.execCommand('insertText', false, txt);
                        elm.dispatchEvent(new InputEvent('input', { bubbles: true }));
                    """, field, text)
                    # Обман React: отправляем пробел + Backspace
                    field.send_keys(" ", Keys.BACKSPACE)
                    time.sleep(0.1)
                    # Отправка Enter
                    field.send_keys(Keys.ENTER)
                    break
                except Exception:
                    time.sleep(1)
            else:
                raise RuntimeError("Не удалось найти/ввести текст в поле комментария")

            logging.info("✅ Комментарий отправлен: %s", text)

            # 6) Логируем статистику
            media_pk = post_url.rstrip("/").split("/")[-1]
            log_comment_stat(username=self.username, media_pk=media_pk, comment_text=text)

            return {"success": True, "comment": text}

        except Exception as e:
            err = traceback.format_exc()
            logging.error("❌ Ошибка при отправке комментария:\n%s", err)
            return {"success": False, "error": err}


    def handle_2fa_code(self, message, bot):
        two_fa_code = message.text  # Получаем код 2FA, который ввел пользователь

        # Находим поле для ввода кода 2FA
        two_fa_input = WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.NAME, 'verificationCode'))
        )

        # Вводим код 2FA в поле
        two_fa_input.send_keys(two_fa_code)

        # Нажимаем кнопку "Submit"
        submit_btn = self.driver.find_element(By.XPATH, "//button[@type='submit']")
        click_element(self.driver, submit_btn)

        # Ожидаем, пока страница не загрузится после ввода кода
        WebDriverWait(self.driver, 15).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        bot.send_message(message.chat.id, "ℹ️ Код 2FA успешно введён.")

        # Продолжаем выполнение других действий после успешного входа
        if self._wait_for_login_success():
            new_cookies = self.driver.get_cookies()
            self._save_cookies_file(new_cookies)
            logging.info("✅ Web login successful and cookies updated")
        else:
            bot.send_message(message.chat.id, "❌ Не удалось выполнить вход после ввода кода 2FA.")

    def get_new_posts(self, profile_url: str, limit: int = 5) -> list:
        """Получает последние посты с профиля"""
        self.driver.get(profile_url)
        time.sleep(3)

        try:
            post_links = WebDriverWait(self.driver, 15).until(
                EC.presence_of_all_elements_located(
                    (By.XPATH,
                     '//a[contains(@href, "/p/")'
                     ' or contains(@href, "/reel/")'
                     ' or contains(@href, "/tv/")]'
                     )
                )
            )

            return [
                InstagramPost(
                    url=link.get_attribute("href"),
                    driver=self.driver
                ) for link in post_links[:limit]
            ]
        except Exception as e:
            logging.error(f"Ошибка получения постов: {str(e)}")
            return []

    def _dismiss_not_now(self, timeout: float = 5.0):
        """
        Пытается нажать все кнопки «Not Now», которые появляются
        (Save Login Info, Turn on Notifications и т.п.).
        """
        buttons_xpath = [
            "//button[text()='Not Now']",
            "//button[contains(., 'Not Now')]",  # на всякий случай
            "//button[text()='Не сейчас']"  # если интерфейс на русском
        ]
        for xpath in buttons_xpath:
            try:
                btn = WebDriverWait(self.driver, timeout).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                click_element(self.driver, btn)
                # после каждого клика даём чуть подумать интерфейсу
                time.sleep(random.uniform(0.5, 1.0))
            except TimeoutException:
                # если по этому XPATH ничего не нашлось — идём дальше
                continue

    def watch_random_story(self, profile_url: str) -> bool:
        try:
            self.driver.get(profile_url)

            # Новый селектор canvas + проверка родительского контейнера
            story_selector = (
                "//div[contains(@role,'button') and .//canvas[contains(@class,'x1upo8f9')]] | "
                "//canvas[@class='x1upo8f9 xpdipgo x87ps6o']"
            )

            # Явное ожидание с комбинированными условиями
            story_element = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.XPATH, story_selector))
            )

            # Прокрутка и анимация
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center', inline: 'center'});",
                story_element
            )

            # Клик через родительский элемент
            parent_element = self.driver.execute_script(
                "return arguments[0].closest('div[role=button]')",
                story_element
            )

            ActionChains(self.driver) \
                .move_to_element(parent_element) \
                .pause(1) \
                .click() \
                .perform()

            # Дополнительная проверка загрузки
            WebDriverWait(self.driver, 10).until(
               EC.visibility_of_element_located((By.XPATH, "//div[@role='dialog']")))

            # Просмотр в течение случайного времени
            time.sleep(random.uniform(4, 7))

            return True

        except Exception as e:
            self.driver.save_screenshot("canvas_error.png")
            return False

