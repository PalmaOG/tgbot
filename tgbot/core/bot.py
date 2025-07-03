import telebot
import logging
from telebot import types
from config.settings import Settings
from managers.database import DatabaseManager
from managers.barber import BarberManager, BarberStorage, QUESTION_ORDER
from managers.keyboard import KeyboardManager
from config.constants import SERVICES
from managers.admin import AdminManager
from managers.client import ClientManager, register_client_handlers
from managers.guide import GuideManager

logger = logging.getLogger(__name__)
bot = telebot.TeleBot(Settings.BOT_TOKEN)
storage = BarberStorage()

def show_main_menu(user_id, message_text=None):
    roles = DatabaseManager.get_all_roles(user_id)
    active_role = DatabaseManager.get_active_role(user_id)
    is_admin = DatabaseManager.is_admin(user_id)
    is_barber_filled = DatabaseManager.barber_exists(user_id) if active_role == 'barber' else False

    markup = KeyboardManager.main_menu(active_role, len(roles), is_admin, is_barber_filled, user_id=user_id)

    if message_text:
        bot.send_message(user_id, message_text, reply_markup=markup)
    else:
        role_name = {
            'client': 'клиент',
            'barber': 'барбер',
            'admin': 'администратор'
        }.get(active_role, active_role)

        text = f"👋 Ваша текущая роль: {role_name}\nВыберите действие:"
        bot.send_message(user_id, text, reply_markup=markup)

def register_handlers():
    @bot.message_handler(commands=['start'])
    def start(message):
        user = message.from_user
        user_id = user.id

        if not DatabaseManager.check_user(user_id):
            if not DatabaseManager.register_user(user_id, user.username, user.first_name):
                return bot.reply_to(message, "⚠️ Ошибка регистрации")

        roles = DatabaseManager.get_all_roles(user_id)
        active_role = DatabaseManager.get_active_role(user_id)

        if active_role == 'barber':
            barber = DatabaseManager.get_barber_by_user_id(user_id)
            if barber:
                status = DatabaseManager.get_barber_status(user_id)
                if status == "banned":
                    bot.send_message(user_id, "❌ Ваша анкета заблокирована за нарушение правил.")
                    return

        if not roles:
            bot.send_message(user_id, "👋 Добро пожаловать! Выберите роль:",
                             reply_markup=KeyboardManager.role_selection_keyboard())
        else:
            show_main_menu(user_id)

    @bot.message_handler(func=lambda msg: msg.text in ["👤 Клиент", "✂️ Барбер"])
    def handle_role_selection(message):
        user_id = message.from_user.id
        role = 'client' if message.text == "👤 Клиент" else 'barber'

        if DatabaseManager.save_user_role(user_id, role):
            show_main_menu(user_id, f"✅ Роль успешно выбрана: {'клиент' if role == 'client' else 'барбер'}")
        else:
            bot.send_message(user_id, "❌ Ошибка выбора роли")

    @bot.message_handler(func=lambda msg: msg.text == "📝 Заполнить анкету барбера")
    def start_barber_questionnaire(message):
        user_id = message.from_user.id

        barber = DatabaseManager.get_barber_by_user_id(user_id)
        if barber:
            status = DatabaseManager.get_barber_status(user_id)
            if status == "banned":
                bot.send_message(user_id, "❌ Ваша анкета заблокирована за нарушение правил.")
                return

        bot.send_message(user_id, "Давайте заполним анкету барбера.",
                         reply_markup=KeyboardManager.barber_questionnaire_keyboard())
        BarberManager.ask_question(user_id, 'description', bot)

    @bot.message_handler(func=lambda msg: msg.text == "✏️ Редактировать анкету")
    def edit_barber_questionnaire(message):
        user_id = message.from_user.id

        barber = DatabaseManager.get_barber_by_user_id(user_id)
        if barber:
            status = DatabaseManager.get_barber_status(user_id)
            if status == "banned":
                bot.send_message(user_id, "❌ Ваша анкета заблокирована за нарушение правил.")
                return

        DatabaseManager.delete_barber_data(user_id)
        storage.clear_profile(user_id)

        bot.send_message(user_id, "✏️ Редактирование анкеты. Начнем заново.",
                         reply_markup=KeyboardManager.barber_questionnaire_keyboard())
        BarberManager.ask_question(user_id, 'description', bot)

    @bot.message_handler(func=lambda msg: msg.text == "💾 Сохранить")
    def save_barber_profile(message):
        user_id = message.from_user.id

        barber = DatabaseManager.get_barber_by_user_id(user_id)
        if barber:
            status = DatabaseManager.get_barber_status(user_id)
            if status == "banned":
                bot.send_message(user_id, "❌ Ваша анкета заблокирована за нарушение правил.")
                return

        BarberManager.save_profile_to_db(user_id, bot)

    @bot.message_handler(func=lambda msg: msg.text in ["➕ Добавить роль", "🔄 Сменить роль"])
    def handle_role_management(message):
        user_id = message.from_user.id

        barber = DatabaseManager.get_barber_by_user_id(user_id)
        if barber:
            status = DatabaseManager.get_barber_status(user_id)
            if status == "banned":
                bot.send_message(user_id, "❌ Ваша анкета заблокирована за нарушение правил.")
                return
        action = message.text

        roles = DatabaseManager.get_all_roles(user_id)
        active_role = DatabaseManager.get_active_role(user_id)
        is_admin = DatabaseManager.is_admin(user_id)

        if action == "➕ Добавить роль":
            available_roles = DatabaseManager.get_available_roles(user_id)
            if not available_roles:
                bot.send_message(user_id, "❌ У вас уже есть все доступные роли.")
                return

            markup = KeyboardManager.available_roles_keyboard(available_roles, is_admin)
            bot.send_message(user_id, "Выберите роль для добавления:", reply_markup=markup)

        elif action == "🔄 Сменить роль":
            if len(roles) < 2:
                bot.send_message(user_id, "❌ У вас только одна роль.")
                return

            markup = KeyboardManager.switch_role_keyboard(roles, active_role, is_admin)
            bot.send_message(user_id, "Выберите роль для переключения:", reply_markup=markup)

    @bot.message_handler(func=lambda msg: "Добавить роль" in msg.text or "Переключиться" in msg.text)
    def handle_role_action(message):
        user_id = message.from_user.id

        if "клиента" in message.text:
            role = 'client'
            action = 'add' if "Добавить" in message.text else 'switch'
        elif "барбера" in message.text:
            role = 'barber'
            action = 'add' if "Добавить" in message.text else 'switch'
        elif "администратора" in message.text:
            role = 'admin'
            action = 'switch'
        else:
            return

        if role == 'admin' and action == 'add':
            return

        if action == 'add':
            if DatabaseManager.save_user_role(user_id, role):
                show_main_menu(user_id, f"✅ Роль успешно добавлена: {role}")
            else:
                bot.send_message(user_id, "❌ Не удалось добавить роль")

        elif action == 'switch':
            if DatabaseManager.switch_active_role(user_id, role):
                show_main_menu(user_id, f"✅ Активная роль изменена: {role}")
            else:
                bot.send_message(user_id, "❌ Не удалось переключить роль")



    @bot.message_handler(func=lambda msg: msg.text in SERVICES.values())
    def handle_service_selection(message):
        user_id = message.from_user.id
        BarberManager.ask_for_service_price(user_id, bot, message.text)

    @bot.message_handler(func=lambda msg: msg.text == "✅ Продолжить")
    def handle_service_continue(message):
        user_id = message.from_user.id
        idx = QUESTION_ORDER.index('services')
        next_key = QUESTION_ORDER[idx + 1]
        BarberManager.ask_question(user_id, next_key, bot)

    @bot.message_handler(func=lambda msg: msg.text == "❌ Отменить заполнение")
    def cancel_questionnaire(message):
        user_id = message.from_user.id
        storage.clear_profile(user_id)
        show_main_menu(user_id, "❌ Заполнение анкеты отменено")

    @bot.message_handler(func=lambda msg: msg.text == "❌ Отмена")
    def cancel_action(message):
        user_id = message.from_user.id
        show_main_menu(user_id)

    @bot.message_handler(func=lambda msg: msg.text == "📍 Выбрать город")
    def choose_city(message):
        user_id = message.from_user.id
        cities = DatabaseManager.get_all_cities()
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for city in cities:
            markup.add(types.KeyboardButton(city))
        markup.add(types.KeyboardButton("❌ Отмена"))
        bot.send_message(user_id, "Выберите город:", reply_markup=markup)
        bot.register_next_step_handler_by_chat_id(user_id, save_city_selection)

    def save_city_selection(message):
        user_id = message.from_user.id
        city_name = message.text.strip()
        if city_name == "❌ Отмена":
            show_main_menu(user_id)
            return
        city_id = DatabaseManager.get_city_id_by_name(city_name)
        if not city_id:
            bot.send_message(user_id, "❌ Город не найден. Попробуйте снова.")
            return choose_city(message)
        DatabaseManager.save_user_city_selection(user_id, city_id)
        bot.send_message(user_id, f"✅ Город выбран: {city_name}", reply_markup=KeyboardManager.main_menu("client", 1, False))
        show_main_menu(user_id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
    def handle_admin_callbacks(call):
        AdminManager.handle_callback(bot, call)

    @bot.message_handler(func=lambda msg: msg.text == "📝 Ждущие анкеты")
    def handle_pending_profiles(message):
        user_id = message.from_user.id
        if not DatabaseManager.is_admin(user_id):
            return bot.send_message(user_id, "❌ У вас нет прав администратора")
        AdminManager.show_pending_profiles(bot, user_id)

    @bot.message_handler(func=lambda msg: msg.text == "📍 Выбрать город")
    def client_choose_city(message):
        user_id = message.from_user.id
        msg = bot.send_message(
            user_id,
            "📍 Введите город, в котором вы хотите искать барбера:",
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(msg, handle_client_city_input)

    def handle_client_city_input(message):
        user_id = message.from_user.id
        city_name = message.text.strip()

        city_id = DatabaseManager.get_city_id_by_name(city_name)
        if not city_id:
            msg = bot.send_message(
                user_id,
                f"❌ Город '{city_name}' не найден в базе. Попробуйте ещё раз:"
            )
            bot.register_next_step_handler(msg, handle_client_city_input)
            return

        DatabaseManager.save_user_city_selection(user_id, city_id)
        bot.send_message(
            user_id,
            f"✅ Город '{city_name}' выбран!",
            reply_markup=KeyboardManager.main_menu(
                "client",
                len(DatabaseManager.get_all_roles(user_id)),
                DatabaseManager.is_admin(user_id)
            )
        )

    @bot.message_handler(func=lambda msg: msg.text == "🔍 Найти барбера")
    def handle_find_barber(message):
        user_id = message.from_user.id
        city_id = DatabaseManager.get_user_city_selection(user_id)
        if not city_id:
            bot.send_message(user_id, "Сначала выберите город через '📍 Выбрать город'.")
            return
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(types.KeyboardButton("🔎 Без фильтров"), types.KeyboardButton("🔎 Фильтры"))
        markup.add(types.KeyboardButton("❌ Отмена"))
        bot.send_message(user_id, "Выберите способ поиска барбера:", reply_markup=markup)

    @bot.message_handler(func=lambda msg: msg.text == "🔎 Без фильтров")
    def handle_find_barber_no_filters(message):
        user_id = message.from_user.id
        city_id = DatabaseManager.get_user_city_selection(user_id)
        ClientManager.show_active_barbers(bot, user_id, page=0, city_id=city_id)

    @bot.message_handler(func=lambda msg: msg.text == "🔎 Фильтры")
    def handle_find_barber_filters(message):
        user_id = message.from_user.id
        city_id = DatabaseManager.get_user_city_selection(user_id)

        has_metro = DatabaseManager.city_has_metro(city_id)

        if has_metro:
            msg = bot.send_message(
                user_id,
                "Введите название станции метро (или отправьте 'нет' если не важно):",
                reply_markup=types.ReplyKeyboardRemove()
            )
            bot.register_next_step_handler(msg, handle_filter_metro)
        else:
            msg = bot.send_message(
                user_id,
                "Введите максимальную цену (до):",
                reply_markup=types.ReplyKeyboardRemove()
            )
            bot.register_next_step_handler(msg, handle_filter_price)

    def handle_filter_metro(message):
        user_id = message.from_user.id
        metro_input = message.text.strip().lower()

        storage = BarberStorage()
        profile = storage.get_profile(user_id) or {}

        if metro_input != 'нет':
            city_id = DatabaseManager.get_user_city_selection(user_id)
            metro_id = DatabaseManager.get_metro_id_by_name(city_id, metro_input)

            if not metro_id:
                msg = bot.send_message(
                    user_id,
                    f"❌ Станция метро '{metro_input}' не найдена. Попробуйте ещё раз или отправьте 'нет':"
                )
                bot.register_next_step_handler(msg, handle_filter_metro)
                return

            profile['filter_metro_id'] = metro_id
        else:
            profile['filter_metro_id'] = None

        storage.save_profile(user_id, profile)

        msg = bot.send_message(
            user_id,
            "Введите максимальную цену (до):",
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(msg, handle_filter_price)

    def handle_filter_price(message):
        user_id = message.from_user.id
        try:
            max_price = int(message.text)
        except ValueError:
            msg = bot.send_message(
                user_id,
                "Пожалуйста, введите число (максимальная цена):"
            )
            bot.register_next_step_handler(msg, handle_filter_price)
            return

        storage = BarberStorage()
        profile = storage.get_profile(user_id) or {}
        profile['filter_max_price'] = max_price
        storage.save_profile(user_id, profile)

        text = (
            "Выберите специализацию, отправив цифру:\n"
            "1 — Борода\n"
            "2 — Длинные волосы\n"
            "3 — Короткие волосы\n"
            "4 — Борода и короткие волосы\n"
            "5 — Борода и длинные волосы\n"
            "6 — Длинные и короткие волосы\n"
            "7 — Все категории"
        )
        msg = bot.send_message(user_id, text)
        bot.register_next_step_handler(msg, handle_filter_specialization)

    def handle_filter_specialization(message):
        user_id = message.from_user.id
        try:
            spec_num = int(message.text)
            if not 1 <= spec_num <= 7:
                raise ValueError
        except ValueError:
            msg = bot.send_message(
                user_id,
                "Пожалуйста, отправьте цифру от 1 до 7."
            )
            bot.register_next_step_handler(msg, handle_filter_specialization)
            return

        storage = BarberStorage()
        profile = storage.get_profile(user_id) or {}
        city_id = DatabaseManager.get_user_city_selection(user_id)

        max_price = profile.get('filter_max_price')
        metro_id = profile.get('filter_metro_id', None)

        barbers = DatabaseManager.get_filtered_barbers(
            city_id=city_id,
            max_price=max_price,
            specialization_num=spec_num,
            metro_id=metro_id
        )

        if not barbers:
            bot.send_message(
                user_id,
                "❌ Нет барберов по выбранным фильтрам."
            )
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add(
                types.KeyboardButton("🔎 Без фильтров"),
                types.KeyboardButton("🔎 Фильтры")
            )
            markup.add(types.KeyboardButton("❌ Отмена"))
            bot.send_message(
                user_id,
                "Выберите способ поиска барбера:",
                reply_markup=markup
            )
            return

        markup = types.InlineKeyboardMarkup()
        for barber in barbers:
            # Используем только первые 10 полей, так как метро теперь не возвращается
            btn_text = f"{barber[9]} ({barber[3]})"
            markup.add(types.InlineKeyboardButton(
                btn_text,
                callback_data=f"client_showbarber_{barber[0]}"
            ))

        bot.send_message(
            user_id,
            "Барберы по фильтрам:",
            reply_markup=markup
        )

    @bot.message_handler(func=lambda msg: msg.text in ["👁️ Скрыть анкету", "👁️ Показать анкету"])
    def handle_toggle_visibility(message):
        user_id = message.from_user.id
        current_role = DatabaseManager.get_active_role(user_id)

        if current_role != 'barber' or not DatabaseManager.barber_exists(user_id):
            return

        current_status = DatabaseManager.get_barber_visibility_status(user_id)

        if current_status not in ['active', 'hidden']:
            return

        new_status = 'hidden' if current_status == 'active' else 'active'
        success = DatabaseManager.update_barber_status_by_user_id(user_id, new_status)

        if success:
            status_text = "скрыта" if new_status == 'hidden' else "доступна для клиентов"
            bot.send_message(
                user_id,
                f"✅ Ваша анкета теперь {status_text}",
                reply_markup=KeyboardManager.main_menu(
                    active_role=current_role,
                    roles_count=len(DatabaseManager.get_all_roles(user_id)),
                    is_admin=DatabaseManager.is_admin(user_id),
                    is_barber_filled=True,
                    user_id=user_id
                )
            )
        else:
            bot.send_message(user_id, "❌ Не удалось изменить видимость анкеты")

    @staticmethod
    def update_barber_status_by_user_id(user_id, new_status):
        with Database() as db:
            if db.connect():
                return db.execute(
                    "UPDATE barbers SET status = %s WHERE user_id = %s",
                    (new_status, user_id)
                )
        return False

    @bot.message_handler(func=lambda msg: msg.text == "👤 Моя анкета")
    def handle_my_profile(message):
        user_id = message.from_user.id
        BarberManager.show_my_profile(user_id, bot)

def start_bot():
    register_handlers()
    register_client_handlers(bot)
    GuideManager.init_handlers(bot)
    print("Бот запущен")
    bot.polling(none_stop=True)

if __name__ == "__main__":
    start_bot()