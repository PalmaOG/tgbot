import mysql.connector
from mysql.connector import Error
from config.settings import Settings

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
                host=Settings.DB_HOST,
                database=Settings.DB_NAME,
                user=Settings.DB_USER,
                password=Settings.DB_PASS
            )
            return True
        except Error as e:
            print(f"Ошибка подключения к БД: {e}")
            return False

    def disconnect(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()

    def execute(self, query, params=None, fetch_one=False):
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params or ())
            result = None
            if query.strip().lower().startswith('select'):
                if fetch_one:
                    result = cursor.fetchone()
                    # ВАЖНО: дочитываем все остальные результаты, чтобы не было "Unread result"
                    cursor.fetchall()
                else:
                    result = cursor.fetchall()
            else:
                self.connection.commit()
                result = True
            cursor.close()
            return result
        except Error as e:
            print(f"Ошибка запроса: {e}")
            return False
