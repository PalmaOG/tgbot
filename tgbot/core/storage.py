import json
import os
from typing import Dict, Optional, List

class BarberStorage:
    def __init__(self, file_path: str = 'barber_profiles.json'):
        self.file_path = file_path
        self._init_storage()

    def _init_storage(self):
        """Создает файл хранилища, если его нет."""
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump({}, f)

    def save_profile(self, user_id: int, answers: Dict[str, any]):
        try:
            # Читаем существующие данные
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                data = {}

            # Обновляем данные
            data[str(user_id)] = answers

            # Записываем данные
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(
                    data,
                    f,
                    indent=4,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(',', ': ')
                )

        except Exception as e:
            print(f"Ошибка при сохранении профиля: {e}")
            raise

    def get_profile(self, user_id: int) -> Dict:
        with open(self.file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get(str(user_id), {})

    def add_work_photo(self, user_id: int, file_id: str):
        """Добавляет file_id в work_photos пользователя."""
        profile = self.get_profile(user_id) or {}
        if 'work_photos' not in profile or not isinstance(profile['work_photos'], list):
            profile['work_photos'] = []
        if file_id not in profile['work_photos']:
            profile['work_photos'].append(file_id)
        self.save_profile(user_id, profile)

    def remove_work_photo(self, user_id: int, file_id: str):
        """Удаляет file_id из work_photos пользователя."""
        profile = self.get_profile(user_id) or {}
        if 'work_photos' in profile and isinstance(profile['work_photos'], list):
            profile['work_photos'] = [fid for fid in profile['work_photos'] if fid != file_id]
            self.save_profile(user_id, profile)

    def clear_work_photos(self, user_id: int):
        """Очищает все рабочие фото пользователя."""
        profile = self.get_profile(user_id) or {}
        profile['work_photos'] = []
        self.save_profile(user_id, profile)

    def clear_profile(self, user_id: int):
        self._init_storage()
        with open(self.file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if str(user_id) in data:
            del data[str(user_id)]
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False, sort_keys=True, separators=(',', ': '))

