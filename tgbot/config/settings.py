import os
class Settings:

    DB_HOST = "localhost"
    DB_NAME = "BarbersMap"
    DB_USER = "root"
    DB_PASS = "root"


    BOT_TOKEN = "7523785900:AAHuHFX6KkI-W0eSCDrnhliCWZBf8W4D5q8"

    @staticmethod
    def db_config():
        return {
            "host": Settings.DB_HOST,
            "database": Settings.DB_NAME,
            "user": Settings.DB_USER,
            "password": Settings.DB_PASS,
        }
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))