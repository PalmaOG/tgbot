import logging
from telebot import types
from telebot.types import ReplyKeyboardRemove, InputMediaPhoto
from config.constants import QUESTIONS, SERVICES
from managers.keyboard import KeyboardManager
from core.storage import BarberStorage
from managers.database import DatabaseManager

logger = logging.getLogger(__name__)
storage = BarberStorage()

QUESTION_ORDER = [
    'description',
    'work_photos',
    'city',
    'metro',
    'experience',
    'specialization',
    'services',
    'instagram',
    'whatsapp',
    'telegram'
]

def russian_years(n):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return f"{n} год"
    elif 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
        return f"{n} года"
    else:
        return f"{n} лет"

class BarberManager:
    @staticmethod
    def show_my_profile(user_id: int, bot):
        """Показывает сохраненную анкету барбера с метро и рейтингом"""
        barber_data = DatabaseManager.get_barber_by_user_id(user_id)
        if not barber_data or len(barber_data) == 0:
            bot.send_message(user_id, "❌ Вы еще не создали анкету барбера.")
            return

        barber_id = barber_data[0]
        profile = DatabaseManager.get_barber_full_data_by_user_id(user_id)
        if not profile:
            bot.send_message(user_id, "❌ Данные анкеты не найдены.")
            return

        avg_rating, rating_count = DatabaseManager.get_barber_average_rating(barber_id)
        rating_text = f"⭐ Рейтинг: {avg_rating:.1f}/5 ({rating_count})\n" if avg_rating is not None else "⭐ Рейтинг: пока нет оценок\n"
        metro_text = f"\n🚇 Метро: {profile['metro_name']}" if profile.get('metro_name') else ""

        services = DatabaseManager.get_barber_services(barber_id)
        services_text = "\n💰 Услуги и цены:\n" if services else "\n💰 Услуги не указаны\n"
        for service in services:
            if isinstance(service, (list, tuple)) and len(service) >= 2:
                services_text += f"• {service[0]}: {float(service[1]):.0f} руб.\n"

        experience_text = russian_years(profile['experience_years']) if profile.get('experience_years') else "Не указано"

        text = (
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 Барбер: {profile['first_name']}\n"
           
            f"📍 Город: {profile['city_name']}{metro_text}\n"
            f"💈 Опыт: {experience_text}\n"
            f"📸 Фото работ: {profile['photos_count']}\n"
            f"{services_text}\n"
            f"📱 Контакты:\n"
            f"  • Instagram: {profile['instagram'] or 'нет'}\n"
            f"  • WhatsApp: {profile['whatsapp'] or 'нет'}\n"
            f"  • Telegram: {profile['telegram'] or 'нет'}\n"
            f"━━━━━━━━━━━━━━━━━━"
        )

        photos = DatabaseManager.get_barber_photos(barber_id)
        if photos:
            try:
                media = [InputMediaPhoto(photo[0] if isinstance(photo, (list, tuple)) else photo) for photo in photos]
                media[0].caption = text
                bot.send_media_group(user_id, media)
            except Exception as e:
                logger.error(f"Ошибка при отправке фото: {e}")
                bot.send_message(user_id, text)
        else:
            bot.send_message(user_id, text)

    @staticmethod
    def ask_question(user_id: int, question_key: str, bot):
        profile = storage.get_profile(user_id) or {}

        if question_key == 'work_photos':
            msg = bot.send_message(
                user_id,
                QUESTIONS['work_photos'],
                reply_markup=ReplyKeyboardRemove()
            )
            bot.register_next_step_handler(msg, BarberManager.handle_work_photo, bot, 0)
            return

        question = QUESTIONS[question_key]

        if question_key == 'specialization':
            selected_specialization = profile.get('specialization')
            bot.send_message(
                user_id,
                question,
                reply_markup=KeyboardManager.specialization_keyboard(selected_specialization)
            )
        else:
            msg = bot.send_message(user_id, question, reply_markup=ReplyKeyboardRemove())
            bot.register_next_step_handler(msg, BarberManager.handle_answer, question_key, bot)

    @staticmethod
    def handle_work_photo(message: types.Message, bot, photo_count):
        user_id = message.from_user.id
        profile = storage.get_profile(user_id) or {}

        # Обработка отмены
        if message.text and message.text.lower() in ['отмена', 'cancel']:
            bot.send_message(user_id, "Загрузка фото отменена.", reply_markup=ReplyKeyboardRemove())
            return

        # Проверка типа контента
        if message.content_type != 'photo':
            msg = bot.send_message(user_id, "Пожалуйста, отправьте именно фото.")
            bot.register_next_step_handler(msg, BarberManager.handle_work_photo, bot, photo_count)
            return

        # Сохранение фото
        file_id = message.photo[-1].file_id
        if 'work_photos' not in profile:
            profile['work_photos'] = []

        if len(profile['work_photos']) >= 5:
            bot.send_message(user_id, "Вы уже загрузили максимальное количество фото (5).")
            BarberManager.ask_question(user_id, 'city', bot)
            return

        profile['work_photos'].append(file_id)
        storage.save_profile(user_id, profile)
        photo_count = len(profile['work_photos'])

        # Проверка количества
        if photo_count < 5:
            remaining = 5 - photo_count
            msg = bot.send_message(
                user_id,
                f"✅ Получено фото: {photo_count}/5. Осталось загрузить: {remaining}",
                reply_markup=ReplyKeyboardRemove()
            )
            bot.register_next_step_handler(msg, BarberManager.handle_work_photo, bot, photo_count)
        else:
            bot.send_message(
                user_id,
                "✅ Все 5 фото успешно загружены! Переходим к следующему шагу.",
                reply_markup=ReplyKeyboardRemove()
            )
            BarberManager.ask_question(user_id, 'city', bot)

    @staticmethod
    def handle_answer(message: types.Message, question_key: str, bot):
        user_id = message.from_user.id
        profile = storage.get_profile(user_id) or {}

        if question_key == 'city':
            city_name = message.text.strip()
            city_id = DatabaseManager.get_city_id_by_name(city_name)
            if not city_id:
                bot.send_message(user_id, f"❌ Город '{city_name}' не найден в базе. Проверьте написание или обратитесь к администратору.")
                msg = bot.send_message(user_id, QUESTIONS['city'], reply_markup=ReplyKeyboardRemove())
                bot.register_next_step_handler(msg, BarberManager.handle_answer, 'city', bot)
                return

            profile['city'] = city_name
            profile['city_id'] = city_id
            storage.save_profile(user_id, profile)

            if DatabaseManager.city_has_metro(city_id):
                BarberManager.ask_question(user_id, 'metro', bot)
            else:
                profile['metro'] = None
                profile['metro_id'] = None
                storage.save_profile(user_id, profile)
                metro_index = QUESTION_ORDER.index('metro')
                next_key = QUESTION_ORDER[metro_index + 1]
                BarberManager.ask_question(user_id, next_key, bot)
            return

        elif question_key == 'metro':
            city_id = profile.get('city_id')
            if not city_id:
                bot.send_message(user_id, "❌ Сначала выберите город.")
                BarberManager.ask_question(user_id, 'city', bot)
                return

            metro_name = message.text.strip()
            metro_id = DatabaseManager.get_metro_id_by_name(city_id, metro_name)
            if not metro_id:
                bot.send_message(user_id, f"❌ Станция метро '{metro_name}' не найдена в выбранном городе. Проверьте написание или выберите другую станцию.")
                BarberManager.ask_question(user_id, 'metro', bot)
                return

            profile['metro'] = metro_name
            profile['metro_id'] = metro_id
            storage.save_profile(user_id, profile)

            idx = QUESTION_ORDER.index('metro')
            next_key = QUESTION_ORDER[idx + 1]
            BarberManager.ask_question(user_id, next_key, bot)
            return

        elif question_key == 'experience':
            if not message.text.isdigit():
                msg = bot.send_message(user_id, "Пожалуйста, введите только цифры (количество лет опыта):")
                bot.register_next_step_handler(msg, BarberManager.handle_answer, question_key, bot)
                return

            profile['experience'] = int(message.text)
            storage.save_profile(user_id, profile)

            idx = QUESTION_ORDER.index(question_key)
            next_key = QUESTION_ORDER[idx + 1]
            BarberManager.ask_question(user_id, next_key, bot)
            return

        elif question_key == 'specialization':
            if message.text not in SERVICES.values():
                bot.send_message(
                    user_id,
                    "Пожалуйста, выберите специализацию из предложенных вариантов.",
                    reply_markup=KeyboardManager.specialization_keyboard(profile.get('specialization'))
                )
                return

            profile['specialization'] = message.text
            profile['services'] = {}
            storage.save_profile(user_id, profile)
            BarberManager.ask_for_service_price(user_id, bot)
            return

        elif question_key in ['instagram', 'whatsapp', 'telegram']:
            profile[question_key] = message.text
            storage.save_profile(user_id, profile)

            idx = QUESTION_ORDER.index(question_key)
            if idx + 1 < len(QUESTION_ORDER):
                next_key = QUESTION_ORDER[idx + 1]
                BarberManager.ask_question(user_id, next_key, bot)
            else:
                BarberManager.finish_questionnaire(user_id, bot)
            return

        profile[question_key] = message.text
        storage.save_profile(user_id, profile)

        idx = QUESTION_ORDER.index(question_key)
        if idx + 1 < len(QUESTION_ORDER):
            next_key = QUESTION_ORDER[idx + 1]
            BarberManager.ask_question(user_id, next_key, bot)
        else:
            BarberManager.finish_questionnaire(user_id, bot)

    @staticmethod
    def ask_for_service_price(user_id: int, bot, service_name=None):
        profile = storage.get_profile(user_id)
        if not profile:
            bot.send_message(user_id, "❌ Ошибка: профиль не найден. Начните анкету заново.")
            return

        if service_name is None:
            if 'specialization' not in profile:
                bot.send_message(
                    user_id,
                    "❌ Сначала выберите специализацию!",
                    reply_markup=KeyboardManager.specialization_keyboard()
                )
                return

            selected_services = list(profile.get('services', {}).keys())
            markup = KeyboardManager.services_keyboard(selected_services)
            bot.send_message(user_id, "Выберите услугу для добавления цены:", reply_markup=markup)
            return

        if service_name:
            msg = bot.send_message(
                user_id,
                f"Укажите среднюю цену для услуги {service_name}:",
                reply_markup=ReplyKeyboardRemove()
            )
            bot.register_next_step_handler(msg, BarberManager.save_service_price, service_name, bot)

    @staticmethod
    def save_service_price(message: types.Message, service_name: str, bot):
        user_id = message.from_user.id
        try:
            price = int(message.text)
        except ValueError:
            bot.send_message(
                user_id,
                "Пожалуйста, введите корректную цену (число):",
                reply_markup=ReplyKeyboardRemove()
            )
            bot.register_next_step_handler(message, BarberManager.save_service_price, service_name, bot)
            return

        profile = storage.get_profile(user_id)
        service_key = next(key for key, val in SERVICES.items() if val == service_name)

        if 'services' not in profile:
            profile['services'] = {}

        profile['services'][service_key] = price
        storage.save_profile(user_id, profile)

        all_services_selected = len(profile.get('services', {})) == len(SERVICES)

        if all_services_selected:
            bot.send_message(
                user_id,
                f"Цена для услуги '{service_name}' сохранена: {price} руб.",
                reply_markup=ReplyKeyboardRemove()
            )
            idx = QUESTION_ORDER.index('services')
            next_key = QUESTION_ORDER[idx + 1]
            BarberManager.ask_question(user_id, next_key, bot)
        else:
            selected_services = list(profile.get('services', {}).keys())
            markup = KeyboardManager.services_keyboard(selected_services)
            bot.send_message(
                user_id,
                f"Цена для услуги '{service_name}' сохранена: {price} руб.\nВыберите следующую услугу или нажмите '✅ Продолжить'.",
                reply_markup=markup
            )

    @staticmethod
    def finish_questionnaire(user_id: int, bot):
        BarberManager.show_profile_for_barber(user_id, bot)

    @staticmethod
    def show_profile_for_barber(user_id: int, bot):
        """Показывает анкету для предпросмотра перед сохранением"""
        profile = storage.get_profile(user_id)
        if not profile:
            bot.send_message(user_id, "❌ Анкета не найдена.")
            return

        # Проверка количества фото перед показом
        if len(profile.get('work_photos', [])) != 5:
            bot.send_message(user_id, "❌ Требуется ровно 5 фото работ!")
            BarberManager.ask_question(user_id, 'work_photos', bot)
            return

        metro_text = f"\n🚇 Метро: {profile['metro']}" if profile.get('metro') else ""

        text = (
            f"👤 Барбер: {profile.get('description', 'Не указано')}\n"
            f"📍 Город: {profile.get('city', 'Не указано')}{metro_text}\n"
            f"💈 Опыт: {russian_years(profile.get('experience', 0)) if profile.get('experience') else 'Не указано'}\n"
        )

        if profile.get('services'):
            text += "\n💰 Услуги и цены:\n"
            for service_key, price in profile['services'].items():
                text += f"• {SERVICES.get(service_key, service_key)}: {price} руб.\n"
        else:
            text += "\n💰 Услуги не указаны\n"

        text += (
            f"\n📱 Контакты:\n"
            f"• Instagram: {profile.get('instagram', 'нет') or 'нет'}\n"
            f"• WhatsApp: {profile.get('whatsapp', 'нет') or 'нет'}\n"
            f"• Telegram: {profile.get('telegram', 'нет') or 'нет'}\n"
        )

        photos = profile.get('work_photos', [])
        markup = KeyboardManager.finish_questionnaire_keyboard()

        if photos:
            try:
                if len(photos) == 1:
                    bot.send_photo(user_id, photos[0], caption=text, reply_markup=markup)
                else:
                    media = [InputMediaPhoto(photo) for photo in photos]
                    media[0].caption = text
                    bot.send_media_group(user_id, media)
                    bot.send_message(user_id, "Ваша анкета:", reply_markup=markup)
            except Exception as e:
                logger.error(f"Ошибка при отправке фото: {e}")
                bot.send_message(user_id, text, reply_markup=markup)
        else:
            bot.send_message(user_id, text, reply_markup=markup)

    @staticmethod
    def save_profile_to_db(user_id: int, bot):
        profile = storage.get_profile(user_id)
        if not profile:
            bot.send_message(user_id, "❌ Профиль не найден.")
            return

        # Жесткая проверка на 5 фото
        if len(profile.get('work_photos', [])) != 5:
            bot.send_message(user_id, "❌ Требуется ровно 5 фото работ!")
            BarberManager.ask_question(user_id, 'work_photos', bot)
            return

        city_name = profile.get('city', '').strip()
        city_id = DatabaseManager.get_city_id_by_name(city_name)
        if not city_id:
            bot.send_message(user_id, f"❌ Город '{city_name}' не найден в базе. Проверьте написание или обратитесь к администратору.")
            return

        metro_id = profile.get('metro_id')

        user_row = DatabaseManager.get_user_by_telegram_id(user_id)
        if not user_row:
            bot.send_message(user_id, "❌ Пользователь не найден в базе.")
            return

        existing_barber = DatabaseManager.get_barber_by_user_id(user_id)
        barber_id = None

        if existing_barber:
            barber_id = existing_barber[0]
            if not DatabaseManager.update_barber(
                    barber_id=barber_id,
                    city_id=city_id,
                    metro_id=metro_id,
                    description=profile.get('description', ''),
                    experience=profile.get('experience', 0),
                    instagram=profile.get('instagram', ''),
                    whatsapp=profile.get('whatsapp', ''),
                    telegram=profile.get('telegram', ''),
                    status='pending'
            ):
                bot.send_message(user_id, "❌ Ошибка при обновлении анкеты.")
                return

            DatabaseManager.delete_barber_portfolio(barber_id)
            DatabaseManager.delete_barber_services(barber_id)

            photos = profile.get('work_photos', [])
            for idx, file_id in enumerate(photos[:5], 1):
                DatabaseManager.insert_barber_portfolio(barber_id, file_id, idx)

            services_data = profile.get('services', {})
            for service_key, price in services_data.items():
                category_id = DatabaseManager.get_category_id_by_type(service_key)
                if not category_id:
                    continue
                service_name = SERVICES.get(service_key, f"Услуга {service_key}")
                DatabaseManager.insert_barber_service(
                    barber_id=barber_id,
                    category_id=category_id,
                    name=service_name,
                    price=price
                )

            storage.clear_profile(user_id)
            bot.send_message(user_id, "✅ Анкета успешно обновлена!")

        else:
            barber_id = DatabaseManager.insert_barber(
                user_id=user_id,
                city_id=city_id,
                metro_id=metro_id,
                description=profile.get('description', ''),
                experience=profile.get('experience', 0),
                instagram=profile.get('instagram', ''),
                whatsapp=profile.get('whatsapp', ''),
                telegram=profile.get('telegram', ''),
                status='pending'
            )

            if not barber_id:
                bot.send_message(user_id, "❌ Не удалось сохранить анкету в базу.")
                return

            photos = profile.get('work_photos', [])
            for idx, file_id in enumerate(photos[:5], 1):
                DatabaseManager.insert_barber_portfolio(barber_id, file_id, idx)

            services_data = profile.get('services', {})
            for service_key, price in services_data.items():
                category_id = DatabaseManager.get_category_id_by_type(service_key)
                if not category_id:
                    continue
                service_name = SERVICES.get(service_key, f"Услуга {service_key}")
                DatabaseManager.insert_barber_service(
                    barber_id=barber_id,
                    category_id=category_id,
                    name=service_name,
                    price=price
                )

            storage.clear_profile(user_id)
            bot.send_message(
                user_id,
                "✅ Анкета успешно сохранена! Теперь вы в базе барберов.",
                reply_markup=types.ReplyKeyboardRemove()
            )

        roles = DatabaseManager.get_all_roles(user_id)
        active_role = DatabaseManager.get_active_role(user_id)
        is_admin = DatabaseManager.is_admin(user_id)
        is_barber_filled = DatabaseManager.barber_exists(user_id)

        markup = KeyboardManager.main_menu(active_role, len(roles), is_admin, is_barber_filled)
        bot.send_message(user_id, "❤️", reply_markup=markup)