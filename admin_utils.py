import json
import os

ADMINS_FILE = "data/admins.json"

# Создание файла, если его нет
def init_admins():
    if not os.path.exists(ADMINS_FILE):
        with open(ADMINS_FILE, "w") as f:
            json.dump([], f)

# Получение списка админов
def get_admins():
    init_admins()
    with open(ADMINS_FILE, "r") as f:
        return json.load(f)

# Проверка, является ли пользователь админом
def is_admin(user_id: int) -> bool:
    return str(user_id) in get_admins()

# Добавление нового админа
def add_admin(user_id: int) -> bool:
    admins = get_admins()
    uid = str(user_id)
    if uid not in admins:
        admins.append(uid)
        with open(ADMINS_FILE, "w") as f:
            json.dump(admins, f)
        return True
    return False

# Удаление админа
def remove_admin(user_id: int) -> bool:
    admins = get_admins()
    uid = str(user_id)
    if uid in admins:
        admins.remove(uid)
        with open(ADMINS_FILE, "w") as f:
            json.dump(admins, f)
        return True
    return False