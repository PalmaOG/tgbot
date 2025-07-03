from telebot import types
from config.constants import SERVICES, HAIRCUT_TYPES
from managers.database import DatabaseManager

class KeyboardManager:
    @staticmethod
    def main_menu(active_role: str, roles_count: int, is_admin: bool, is_barber_filled: bool = False, user_id: int = None):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

        if active_role == 'barber':
            if is_barber_filled:
                markup.add(types.KeyboardButton("👤 Моя анкета"))  # Добавлена кнопка "Моя анкета"
                markup.add(types.KeyboardButton("✏️ Редактировать анкету"))
                current_status = DatabaseManager.get_barber_visibility_status(user_id)
                if current_status in ['active', 'hidden']:
                    btn_text = "👁️ Скрыть анкету" if current_status == 'active' else "👁️ Показать анкету"
                    markup.add(types.KeyboardButton(btn_text))
            else:
                markup.add(types.KeyboardButton("📝 Заполнить анкету барбера"))
        elif active_role == 'client':
            markup.add(
                types.KeyboardButton("🔍 Найти барбера"),
                types.KeyboardButton("📍 Выбрать город"),
                types.KeyboardButton("📚 Справочник"),
                types.KeyboardButton("⭐ Избранное")
            )
        elif active_role == 'admin':
            markup.add(types.KeyboardButton("📝 Ждущие анкеты"))

        role_buttons = []
        if roles_count > 1:
            role_buttons.append(types.KeyboardButton("🔄 Сменить роль"))
        if roles_count < 2 or is_admin:
            role_buttons.append(types.KeyboardButton("➕ Добавить роль"))

        if role_buttons:
            markup.row(*role_buttons)

        return markup

    @staticmethod
    def profile_management_keyboard():
        """Клавиатура для управления анкетой (редактировать/удалить)"""
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("✏️ Редактировать", callback_data="edit_profile"),
            types.InlineKeyboardButton("❌ Удалить", callback_data="delete_profile")
        )
        markup.add(types.InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_menu"))
        return markup

    @staticmethod
    def confirm_delete_keyboard():
        """Клавиатура подтверждения удаления анкеты"""
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("✅ Да", callback_data="confirm_delete"),
            types.InlineKeyboardButton("❌ Нет", callback_data="cancel_delete")
        )
        return markup

    @staticmethod
    def admin_main_keyboard():
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("📝 Ждущие анкеты"))
        return markup

    @staticmethod
    def role_selection_keyboard():
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(
            types.KeyboardButton("👤 Клиент"),
            types.KeyboardButton("✂️ Барбер")
        )
        return markup

    @staticmethod
    def available_roles_keyboard(available_roles: list, is_admin: bool):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for role in available_roles:
            if role == 'client':
                markup.add(types.KeyboardButton("👤 Добавить роль клиента"))
            elif role == 'barber':
                markup.add(types.KeyboardButton("✂️ Добавить роль барбера"))

        if is_admin:
            markup.add(types.KeyboardButton("👑 Переключиться на администратора"))

        markup.add(types.KeyboardButton("❌ Отмена"))
        return markup

    @staticmethod
    def switch_role_keyboard(roles: list, active_role: str, is_admin: bool):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for role in roles:
            if role == 'client' and role != active_role:
                markup.add(types.KeyboardButton("👤 Переключиться на клиента"))
            elif role == 'barber' and role != active_role:
                markup.add(types.KeyboardButton("✂️ Переключиться на барбера"))

        if is_admin and 'admin' != active_role:
            markup.add(types.KeyboardButton("👑 Переключиться на администратора"))

        markup.add(types.KeyboardButton("❌ Отмена"))
        return markup

    @staticmethod
    def barber_questionnaire_keyboard():
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("❌ Отменить заполнение"))
        return markup

    @staticmethod
    def specialization_keyboard(selected_specialization=None):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for service in SERVICES.values():
            if service != selected_specialization:
                markup.add(types.KeyboardButton(service))
        return markup

    @staticmethod
    def services_keyboard(selected_services=None):
        if selected_services is None:
            selected_services = []

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        available_services = [val for key, val in SERVICES.items() if key not in selected_services]

        row = []
        for service in available_services:
            row.append(types.KeyboardButton(service))
            if len(row) == 2:
                markup.row(*row)
                row = []

        if row:
            markup.row(*row)

        if selected_services:
            markup.add(types.KeyboardButton("✅ Продолжить"))

        return markup

    @staticmethod
    def finish_questionnaire_keyboard():
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("✏️ Редактировать анкету"))
        markup.add(types.KeyboardButton("💾 Сохранить"))
        return markup

    @staticmethod
    def client_main_menu():
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        buttons = [
            "🔍 Найти барбера",
            "📍 Выбрать город",
            "📚 Справочник",
            "⭐ Избранное"
        ]
        markup.add(*buttons)
        return markup

    @staticmethod
    def get_guide_categories():
        markup = types.InlineKeyboardMarkup()
        for category_type, name in HAIRCUT_TYPES.items():
            markup.add(types.InlineKeyboardButton(
                name,
                callback_data=f"guide_category_{category_type}"
            ))
        return markup

    @staticmethod
    def get_haircuts_keyboard(haircuts, back_callback="guide_back_to_categories"):
        markup = types.InlineKeyboardMarkup()
        for haircut in haircuts:
            markup.add(types.InlineKeyboardButton(
                haircut[1],  # name
                callback_data=f"guide_haircut_{haircut[0]}"  # id
            ))
        markup.add(types.InlineKeyboardButton(
            "🔙 Назад",
            callback_data=back_callback
        ))
        return markup

    # В классе KeyboardManager добавим метод:
    @staticmethod
    def admin_filters():
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("📋 Список анкет", "🔍 Фильтр по городу")
        markup.add("⬅️ В главное меню")
        return markup