
# ├── core/accounts.py — ротация, лимиты, прокси

import logging
import random
from urllib.parse import urlparse
from auth.selenium_auth import SeleniumSessionManager
from auth.inst_auth import InstaAuthManager

ACCOUNTS_ROTATION = []
INSTAGRAM_ACCOUNTS = []  # импортируй откуда нужно или передавай как аргумент


def is_valid_proxy(proxy: str) -> bool:
    try:
        parsed = urlparse(proxy)
        return all([parsed.scheme, parsed.hostname, parsed.port])
    except Exception:
        return False


def init_accounts_rotation(account_data):
    global ACCOUNTS_ROTATION
    ACCOUNTS_ROTATION = []

    success, twofa, failed = 0, 0, 0

    for acc in account_data:
        username = acc.get("username")
        password = acc.get("password")
        proxy = acc.get("proxy")

        logging.info(f"🌐 Инициализация: {username} (proxy: {proxy or 'нет'})")

        # Проверка прокси
        if proxy and not is_valid_proxy(proxy):
            logging.warning(f"⚠️ Прокси для {username} некорректен: {proxy}")
            proxy = None

        # Попытка через instagrapi для сохранения сессии/авторизации
        auth_manager = InstaAuthManager(username, password, proxy)
        result = auth_manager.login()

        if result.get("2fa_required"):
            logging.warning(f"🔐 Требуется 2FA: {username}")
            twofa += 1
            continue
        if not result.get("success"):
            logging.error(f"❌ Ошибка входа: {result.get('error')}")
            failed += 1
            continue

        # Успешно — добавляем в ротацию с Selenium для комментинга
        session = SeleniumSessionManager(username, password, proxy)
        try:
            session.login()
            ACCOUNTS_ROTATION.append(session)
            logging.info(f"✅ Selenium-сессия готова: {username}")
            success += 1
        except Exception as e:
            logging.error(f"⚠️ Selenium вход не удался для {username}: {e}")
            failed += 1

    logging.info("🔁 Инициализация завершена")
    logging.info(f"  ✅ Успешно: {success}")
    logging.info(f"  🔐 2FA: {twofa}")
    logging.info(f"  ❌ Ошибок: {failed}")


def pick_account():
    if not ACCOUNTS_ROTATION:
        logging.warning("⚠️ Нет доступных аккаунтов для ротации.")
        return None
    return random.choice(ACCOUNTS_ROTATION)


def get_accounts():
    return ACCOUNTS_ROTATION
