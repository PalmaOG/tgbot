import logging
import mysql.connector
from mysql.connector import Error
from telebot import TeleBot, types

# Конфигурация (замените значения на свои)
CONFIG = {
    'DB_HOST': 'localhost',
    'DB_NAME': 'BarbersMap',
    'DB_USER': 'root',
    'DB_PASS': 'root',
    'BOT_TOKEN': '7523785900:AAHuHFX6KkI-W0eSCDrnhliCWZBf8W4D5q8'
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.connection = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=CONFIG['DB_HOST'],
                database=CONFIG['DB_NAME'],
                user=CONFIG['DB_USER'],
                password=CONFIG['DB_PASS']
            )
            return True
        except Error as e:
            logger.error(f"Ошибка подключения к БД: {e}")
            return False

    def disconnect(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()

    def execute(self, query, params=None, fetch_one=False):
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params or ())

            if query.strip().lower().startswith('select'):
                if fetch_one:
                    result = cursor.fetchone()
                    cursor.fetchall()
                else:
                    result = cursor.fetchall()
            else:
                self.connection.commit()
                result = True

            cursor.close()
            return result
        except Error as e:
            logger.error(f"Ошибка запроса: {e}")
            return False

class GuidePhotoFiller:
    def __init__(self, bot_token):
        self.bot = TeleBot(bot_token)
        self.current_haircut_id = None

        # Регистрируем обработчики
        self.bot.message_handler(commands=['start', 'help'])(self.handle_start)
        self.bot.message_handler(commands=['set_haircut'])(self.handle_set_haircut)
        self.bot.message_handler(content_types=['photo'])(self.handle_photo)

    def handle_start(self, message):
        help_text = """
📌 <b>Использование:</b>
1. Установите ID стрижки: <code>/set_haircut ID</code>
   Пример: <code>/set_haircut 1</code>
2. Отправляйте фото по одному
3. Фото будут автоматически добавляться в базу
"""
        self.bot.reply_to(message, help_text, parse_mode='HTML')

    def handle_set_haircut(self, message):
        try:
            _, haircut_id = message.text.split()
            self.current_haircut_id = int(haircut_id)

            with Database() as db:
                if db.connect():
                    result = db.execute(
                        "SELECT name FROM haircut_guide WHERE id = %s",
                        (self.current_haircut_id,),
                        fetch_one=True
                    )
                    if not result:
                        return self.bot.reply_to(message, "❌ Стрижка с таким ID не найдена")

                    name = result[0]

            self.bot.reply_to(
                message,
                f"✅ Установлен ID стрижки: <b>{self.current_haircut_id}</b>\n"
                f"✂️ Название: <b>{name}</b>\n\n"
                "Теперь отправляйте фото по одному",
                parse_mode='HTML'
            )
        except (ValueError, IndexError):
            self.bot.reply_to(message, "❌ Использование: /set_haircut ID\nНапример: /set_haircut 1")

    def handle_photo(self, message):
        if not self.current_haircut_id:
            return self.bot.reply_to(
                message,
                "❌ Сначала установите ID стрижки командой /set_haircut ID"
            )

        file_id = message.photo[-1].file_id

        try:
            with Database() as db:
                if db.connect():
                    # Упрощенный запрос без использования position
                    success = db.execute(
                        "INSERT INTO haircut_guide_photos (haircut_id, photo_url, is_primary) "
                        "VALUES (%s, %s, %s)",
                        (
                            self.current_haircut_id,
                            file_id,
                            1  # Первое фото всегда будет основным
                        )
                    )

                    if success:
                        self.bot.reply_to(
                            message,
                            f"✅ <b>Фото добавлено!</b>\n"
                            f"ID стрижки: <code>{self.current_haircut_id}</code>",
                            parse_mode='HTML'
                        )
                    else:
                        self.bot.reply_to(message, "❌ Ошибка при сохранении фото в базу")
        except Exception as e:
            logger.error(f"Ошибка при сохранении фото: {e}")
            self.bot.reply_to(message, "❌ Произошла ошибка при обработке фото")

    def start(self):
        logger.info("Бот для заполнения фото справочника запущен...")
        self.bot.polling()

if __name__ == '__main__':
    if not CONFIG['BOT_TOKEN'] or CONFIG['BOT_TOKEN'] == 'ВАШ_ТОКЕН_БОТА':
        logger.error("❌ Не задан токен бота в CONFIG!")
        exit(1)

    filler = GuidePhotoFiller(CONFIG['BOT_TOKEN'])
    filler.start()