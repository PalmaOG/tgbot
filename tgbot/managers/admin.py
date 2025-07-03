from telebot import types
from managers.database import DatabaseManager
from managers.keyboard import KeyboardManager

class AdminManager:
    @staticmethod
    def show_pending_profiles(bot, user_id, page=0, city_id=None):
        """Показывает список анкет как inline-кнопки с пагинацией"""
        if not DatabaseManager.is_admin(user_id):
            return bot.send_message(user_id, "❌ У вас нет прав администратора")

        pending_profiles = DatabaseManager.get_pending_profiles(page, city_id=city_id)
        if not pending_profiles:
            return bot.send_message(user_id, "✅ Нет анкет на рассмотрении.")

        markup = types.InlineKeyboardMarkup()
        for profile in pending_profiles:
            full_profile = DatabaseManager.get_barber_full_data_by_user_id(profile[1])
            metro_text = f" ({full_profile['metro_name']})" if full_profile and full_profile.get('metro_name') else ""

            btn_text = f"{profile[9]}{metro_text} ({profile[3]})"
            markup.add(types.InlineKeyboardButton(
                btn_text,
                callback_data=f"admin_view_profile_{profile[0]}"
            ))

        nav_buttons = []
        if page > 0:
            nav_buttons.append(types.InlineKeyboardButton(
                "⬅️ Назад",
                callback_data=f"admin_pending_prev_{page-1}_{city_id if city_id else ''}"
            ))
        if len(pending_profiles) == 10:
            nav_buttons.append(types.InlineKeyboardButton(
                "Вперёд ➡️",
                callback_data=f"admin_pending_next_{page+1}_{city_id if city_id else ''}"
            ))

        if nav_buttons:
            markup.row(*nav_buttons)

        if city_id:
            city_name = DatabaseManager.get_city_name_by_id(city_id)
            markup.add(types.InlineKeyboardButton(
                "🔙 Сбросить фильтр",
                callback_data="admin_reset_filter"
            ))
            title = f"Анкеты на модерацию в городе {city_name} (страница {page+1}):"
        else:
            markup.add(types.InlineKeyboardButton(
                "🔍 Фильтр по городу",
                callback_data="admin_filter_by_city"
            ))
            title = f"Анкеты на модерацию (страница {page+1}):"

        bot.send_message(user_id, title, reply_markup=markup)

    @staticmethod
    def ask_for_city_filter(bot, user_id):
        """Запрашивает у администратора город для фильтрации"""
        msg = bot.send_message(
            user_id,
            "🏙 Введите название города для фильтрации анкет:",
            reply_markup=types.ForceReply()
        )
        bot.register_next_step_handler(msg, lambda m: AdminManager.handle_city_filter(bot, m))

    @staticmethod
    def handle_city_filter(bot, message):
        """Обрабатывает ввод города для фильтрации"""
        user_id = message.from_user.id
        city_name = message.text.strip()

        if not city_name:
            msg = bot.send_message(
                user_id,
                "❌ Название города не может быть пустым. Попробуйте еще раз:",
                reply_markup=types.ForceReply()
            )
            bot.register_next_step_handler(msg, lambda m: AdminManager.handle_city_filter(bot, m))
            return

        city_id = DatabaseManager.get_city_id_by_name(city_name)
        if not city_id:
            bot.send_message(
                user_id,
                f"❌ Город '{city_name}' не найден",
                reply_markup=KeyboardManager.admin_main_keyboard()
            )
            return

        AdminManager.show_pending_profiles(bot, user_id, city_id=city_id)

    @staticmethod
    def show_profile_details(bot, user_id, barber_id):
        """Показывает полную анкету с кнопками действий"""
        profile = DatabaseManager.get_barber_by_id(barber_id)
        if not profile:
            return bot.send_message(user_id, "❌ Анкета не найдена")

        full_profile = DatabaseManager.get_barber_full_data_by_user_id(profile['user_id'])
        metro_text = f"\n🚇 Метро: {full_profile['metro_name']}" if full_profile and full_profile.get('metro_name') else ""

        # Форматирование текста для опыта
        experience = profile['experience_years']
        if experience == 1:
            experience_text = "1 год"
        elif 2 <= experience <= 4:
            experience_text = f"{experience} года"
        else:
            experience_text = f"{experience} лет"

        services = DatabaseManager.get_barber_services(barber_id)
        services_text = ""
        if services:
            services_text = "\n💰 Услуги и цены:\n"
            for service in services:
                if isinstance(service, (list, tuple)) and len(service) >= 2:
                    services_text += f"• {service[0]}: {int(service[1])} руб.\n"

        text = (
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🆔 ID: {profile['id']}\n"
            f"👤 Барбер: {profile['first_name']}\n"
            f"📍 Город: {profile['city_name']}{metro_text}\n"
            f"💈 Опыт: {experience_text}\n"
            f"📸 Фото работ: {profile['photos_count']}\n"
            f"{services_text}"
            f"📱 Контакты:\n"
            f"  • Instagram: {profile['instagram'] or 'нет'}\n"
            f"  • WhatsApp: {profile['whatsapp'] or 'нет'}\n"
            f"  • Telegram: {profile['telegram'] or 'нет'}\n"
            f"━━━━━━━━━━━━━━━━━━"
        )

        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("✅ Одобрить", callback_data=f"admin_approve_{barber_id}"),
            types.InlineKeyboardButton("🚫 Забанить", callback_data=f"admin_ban_{barber_id}")
        )
        markup.add(types.InlineKeyboardButton(
            "💬 Оставить комментарий",
            callback_data=f"admin_comment_{barber_id}"
        ))
        markup.add(types.InlineKeyboardButton(
            "🔙 Назад к списку",
            callback_data="admin_back_to_list"
        ))

        photos = DatabaseManager.get_barber_photos(barber_id)
        if photos:
            try:
                media = [types.InputMediaPhoto(photos[0][0], caption=text)]
                for photo in photos[1:]:
                    media.append(types.InputMediaPhoto(photo[0]))
                bot.send_media_group(user_id, media)
                bot.send_message(user_id, "Выберите действие:", reply_markup=markup)
            except Exception as e:
                print(f"Ошибка отправки фото: {e}")
                bot.send_message(user_id, text, reply_markup=markup)
        else:
            bot.send_message(user_id, text, reply_markup=markup)
    @staticmethod
    def handle_comment_input(bot, message, barber_id):
        """Обрабатывает ввод комментария администратора"""
        user_id = message.from_user.id
        comment = message.text

        if not comment or len(comment.strip()) < 5:
            msg = bot.send_message(
                user_id,
                "❌ Комментарий должен содержать не менее 5 символов. Попробуйте еще раз:",
                reply_markup=types.ForceReply()
            )
            bot.register_next_step_handler(
                msg,
                lambda m: AdminManager.handle_comment_input(bot, m, barber_id)
            )
            return

        barber_user_id = DatabaseManager.get_barber_user_id(barber_id)
        if barber_user_id:
            bot.send_message(
                barber_user_id,
                f"📝 Комментарий администратора к вашей анкете:\n\n{comment}"
            )

        # Создаем клавиатуру с дополнительными кнопками
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row(types.KeyboardButton("📝 Ждущие анкеты"))  # Одна кнопка на всю строку
        markup.row(  # Две кнопки в следующей строке
            types.KeyboardButton("🔄 Сменить роль"),
        types.KeyboardButton("➕ Добавить роль")

    )

        bot.send_message(
            user_id,
            f"✅ Комментарий отправлен барберу\n\nВыберите дальнейшее действие:",
            reply_markup=markup
        )

        # Показываем детали анкеты снова (опционально)
        AdminManager.show_profile_details(bot, user_id, barber_id)
    @staticmethod
    def handle_callback(bot, call):
        user_id = call.from_user.id
        data = call.data

        try:
            if data.startswith("admin_pending_prev_") or data.startswith("admin_pending_next_"):
                parts = data.split('_')
                page = int(parts[3])
                city_id = int(parts[4]) if len(parts) > 4 and parts[4] else None
                AdminManager.show_pending_profiles(bot, user_id, page, city_id)

            elif data.startswith("admin_view_profile_"):
                barber_id = int(data.split("_")[3])
                AdminManager.show_profile_details(bot, user_id, barber_id)

            elif data == "admin_back_to_list":
                AdminManager.show_pending_profiles(bot, user_id)

            elif data.startswith("admin_approve_"):
                barber_id = int(data.split("_")[2])
                DatabaseManager.update_barber_status(barber_id, "active")
                barber_user_id = DatabaseManager.get_barber_user_id(barber_id)
                bot.send_message(barber_user_id, "🎉 Ваша анкета одобрена! Теперь вы видимы в поиске. Ведите /start")
                bot.answer_callback_query(call.id, "✅ Анкета одобрена")
                AdminManager.show_pending_profiles(bot, user_id)

            elif data.startswith("admin_ban_"):
                barber_id = int(data.split("_")[2])
                DatabaseManager.update_barber_status(barber_id, "banned")
                barber_user_id = DatabaseManager.get_barber_user_id(barber_id)
                bot.send_message(barber_user_id, "❌ Ваша анкета заблокирована за нарушение правил.")
                bot.answer_callback_query(call.id, "🚫 Анкета заблокирована")
                AdminManager.show_pending_profiles(bot, user_id)

            elif data.startswith("admin_comment_"):
                barber_id = int(data.split("_")[2])
                msg = bot.send_message(
                    user_id,
                    "✏️ Введите ваш комментарий для барбера:",
                    reply_markup=types.ForceReply()
                )
                bot.register_next_step_handler(
                    msg,
                    lambda m: AdminManager.handle_comment_input(bot, m, barber_id)
                )
                bot.answer_callback_query(call.id, "💬 Введите комментарий")

            elif data == "admin_filter_by_city":
                AdminManager.ask_for_city_filter(bot, user_id)
                bot.answer_callback_query(call.id)

            elif data == "admin_reset_filter":
                AdminManager.show_pending_profiles(bot, user_id)
                bot.answer_callback_query(call.id)

            bot.answer_callback_query(call.id)
        except Exception as e:
            bot.send_message(user_id, f"❌ Ошибка: {str(e)}")
            bot.answer_callback_query(call.id)