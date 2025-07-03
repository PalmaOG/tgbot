from core.bot import start_bot
from core.database import Database
from config.settings import Settings

def check_db_connection():
    with Database() as db:
        if db.connect():
            print("✅ Подключение к БД успешно")
            return True
    print("❌ Ошибка подключения к БД")
    return False

if __name__ == "__main__":
    if check_db_connection():
        start_bot()