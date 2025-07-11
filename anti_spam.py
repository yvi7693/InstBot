# anti_spam.py

import logging
from datetime import datetime, timedelta
import time
import random
import asyncio
from collections import defaultdict, deque
from typing import Callable, Deque, Dict, Any

from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By

from auth.selenium_auth import click_element


class AntiSpamController:
    def __init__(self,
        max_comments_per_hour=8,
        max_comments_per_day=40,
        max_stories=20,
        human_delay_range=(3.0, 12.0)
    ):
        self.max_comments_per_hour = max_comments_per_hour
        self.max_comments_per_day = max_comments_per_day
        self.max_stories = max_stories
        self.human_delay_range = human_delay_range
        self.comment_log = []
        self.story_log = deque(maxlen=100)

    def human_delay(self):
        """Случайная задержка с экспоненциальным распределением"""
        delay = random.expovariate(1.0 / 5.0) + 1.0  # Средняя задержка 6 сек
        time.sleep(min(max(delay, 2.0), 15.0))

    async def human_like_pause(self):
        # имитация чтения ленты или сторис
        await self.human_like_pause()

    def human_typing_delay(self, text: str):
        """Задержка, имитирующая набор текста"""
        for _ in text:
            time.sleep(random.uniform(0.08, 0.3))

    def can_watch_story(self):  # исправлено название метода
        """Проверка лимита просмотров сторис"""
        last_hour = datetime.now() - timedelta(hours=1)
        return len([t for t in self.story_log if t > last_hour]) < self.max_stories

    def log_story(self):
        """Фиксируем просмотр"""
        self.story_log.append(datetime.now())

    def log_comment(self):
        now = datetime.now()
        self.comment_log.append(now)

    def can_comment(self) -> bool:
        now = datetime.now()
        hourly = [t for t in self.comment_log if now - t < timedelta(hours=1)]
        daily = [t for t in self.comment_log if now - t < timedelta(days=1)]
        return len(hourly) < self.max_comments_per_hour and len(daily) < self.max_comments_per_day

    def maybe_take_break(self):
        """
        С вероятностью 10% бот уходит в перерыв на 5–15 минут.
        """
        if random.random() < 0.1:
            pause = random.randint(3, 10)
            logging.info(f"🛑 Антиспам-пауза: {pause} секунд")
            time.sleep(pause)

    async def random_like_posts(self,
                                posts: list,
                                like_probability: float = 0.2,
                                min_delay: float = 1.0,
                                max_delay: float = 3.0):
        """
        Во время мониторинга новых постов с вероятностью like_probability
        бот лайкает случайный пост из списка posts.

        :param posts: список новых постов (объектов с методом like()).
        :param like_probability: вероятность лайка одного из новых постов.
        :param min_delay: минимальная задержка между лайками в секундах.
        :param max_delay: максимальная задержка между лайками в секундах.
        """
        # Проверяем, стоит ли лайкнуть
        if not posts or random.random() >= like_probability:
            return

        # Выбираем случайный пост
        post = random.choice(posts)
        try:
            # Предполагается, что у объекта post есть async-метод like()
            await post.like()
            logging.info(f"❤️ Лайкнул рандомный пост {getattr(post, 'id', 'unknown')}")
        except Exception as e:
            logging.error(f"Ошибка при лайке поста {getattr(post, 'id', 'unknown')}: {e}")
        finally:
            # Небольшая задержка, чтобы не выглядеть слишком «роботически»
            await self.human_like_pause()

    async def view_random_stories(self, driver):
        """
        Эмулирует просмотр до 3 Stories подряд.
        """
        # найдем все точки со сторис (canvas с aria-label)
        stories = driver.find_elements(By.CSS_SELECTOR, 'canvas[aria-label]')
        if not stories:
            return

        # возьмем случайные до 3
        to_view = random.sample(stories, min(len(stories), 3))
        for item in to_view:
            # плавный клик по иконке
            actions = ActionChains(driver)
            actions.move_to_element(item)
            actions.pause(random.uniform(0.5, 1.5))
            actions.click()
            actions.perform()

            # посмотреть сторис 3–7 секунд
            await asyncio.sleep(random.uniform(3.0, 7.0))

            # закрыть сторис — нажать по любому месту вне видео
            driver.execute_script(
                "document.querySelector('body').click();"
            )
            await asyncio.sleep(random.uniform(1.0, 2.0))

    async def run(self, driver, targets, comment_text="Отлично!"):
        """
        Основной цикл работы бота: каждые 10 комментариев — просмотр сторис,
        отправка одинакового комментария с паузами и ограничениями.
        """
        for i, target in enumerate(targets):
            # Эмуляция просмотра сторис раз в 10 итераций
            if i > 0 and i % 10 == 0:
                await self.view_random_stories(driver)

            # Статический комментарий без генерации
            text_to_comment = comment_text

            # Открыть поле для комментария и отправить
            comment_icon = driver.find_element(By.CSS_SELECTOR, '...')
            click_element(driver, comment_icon)
            await asyncio.sleep(random.uniform(1.0, 2.5))

            field = driver.find_element(By.CSS_SELECTOR, 'textarea')
            click_element(driver, field)
            field.send_keys(text_to_comment)

            submit_btn = driver.find_element(By.CSS_SELECTOR, 'button[type=submit]')
            click_element(driver, submit_btn)

            # Лимиты по количеству
            self.comment_log.append(time.time())
            if len(self.comment_log) >= self.max_comments_per_hour:
                rest = random.uniform(1800, 3600)
                logging.info(f"Превышен часовой лимит, сплю {rest / 60:.1f} мин")
                await asyncio.sleep(rest)

            # Человеко-подобная пауза перед следующим действием
            await asyncio.sleep(random.uniform(*self.human_delay_range))

# Пример использования в коде мониторинга (например, в другом модуле):
#
# controller = AntiSpamController()
# while True:
#     new_posts = await fetch_new_posts()
#     await controller.random_like_posts(new_posts)
#     controller.maybe_take_break()
#     # ...другая логика спама/комментариев
