import os
import logging
from instagrapi import Client
from instagrapi.exceptions import TwoFactorRequired, ChallengeRequired

# inst_auth.py

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSIONS_DIR = os.path.join(BASE_DIR, '..', 'sessions')
os.makedirs(SESSIONS_DIR, exist_ok=True)

class InstaAuthManager:
    """
    Менеджер авторизации Instagram через instagrapi с поддержкой 2FA и challenge.
    Используйте метод login() для начальной попытки входа. Если вернёт 2fa_required или challenge_required,
    далее вызовите submit_2fa(code) или challenge_resolve(code) соответственно.
    """
    def __init__(self, username: str, password: str, proxy: str = None):
        self.username = username
        self.password = password
        self.client = Client()
        if proxy:
            self.client.set_proxy(proxy)
        self.session_path = os.path.join(SESSIONS_DIR, f"{username}.json")
        self.waiting_for_2fa = False
        self.waiting_for_challenge = False

    def login(self) -> dict:
        """
        Пытается войти:
          - при success=True сессия авторизована;
          - при 2fa_required=True необходимо вызвать submit_2fa(code);
          - при challenge_required=True необходимо вызвать challenge_resolve(code).
        """
        # попытка загрузить и использовать сохранённую сессию
        if os.path.exists(self.session_path):
            try:
                self.client.load_settings(self.session_path)
                self.client.login(self.username, self.password)
                logging.info(f"✅ Сессия загружена для {self.username}")
                return {"success": True}
            except Exception as e:
                logging.warning(f"⚠️ Не удалось загрузить сессию: {e}")
        # полный вход
        try:
            self.client.login(self.username, self.password)
            self._save_session()
            logging.info(f"✅ Успешный вход для {self.username}")
            return {"success": True}
        except TwoFactorRequired:
            # Пометка, что требуется ввод кода 2FA
            self.waiting_for_2fa = True
            logging.info("🔐 Требуется 2FA")
            return {"success": False, "error": "2FA_REQUIRED", "2fa_required": True}
        except ChallengeRequired:
            self.waiting_for_challenge = True
            logging.info("⚠️ Требуется Challenge (email/SMS)")
            return {"success": False, "error": "CHALLENGE_REQUIRED", "challenge_required": True}
        except Exception as e:
            logging.error(f"❌ Ошибка входа: {e}")
            return {"success": False, "error": str(e)}

    def submit_2fa(self, code: str) -> dict:
        """
        Завершает вход, передав вручную полученный код 2FA.
        """
        if not self.waiting_for_2fa:
            return {"success": False, "error": "NO_2FA_REQUEST"}
        try:
            # Повторный вызов login с передачей verification_code
            success = self.client.login(
                self.username,
                self.password,
                verification_code=code
            )
            if success:
                self._save_session()
                self.waiting_for_2fa = False
                logging.info(f"✅ 2FA подтверждён для {self.username}")
                return {"success": True}
            else:
                return {"success": False, "error": "FAILED_2FA"}
        except Exception as e:
            logging.error(f"❌ Ошибка 2FA: {e}")
            return {"success": False, "error": str(e)}

    def challenge_resolve(self, code: str) -> bool:
        """
        Завершает Challenge-кодом из email или SMS.
        """
        if not self.waiting_for_challenge:
            return False
        try:
            self.client.challenge_resolve(code)
            self._save_session()
            self.waiting_for_challenge = False
            logging.info(f"✅ Challenge пройден для {self.username}")
            return True
        except Exception as e:
            logging.error(f"❌ Ошибка Challenge: {e}")
            return False

    def _save_session(self):
        try:
            self.client.dump_settings(self.session_path)
            logging.info(f"💾 Сохранена сессия: {self.session_path}")
        except Exception as e:
            logging.error(f"❌ Не удалось сохранить сессию: {e}")

    def get_client(self) -> Client:
        return self.client
