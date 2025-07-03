from telebot import types
from managers.database import DatabaseManager
from managers.keyboard import KeyboardManager
from managers.barber import BarberStorage

def plural_years(n):
    n = abs(n)
    if n % 10 == 1 and n % 100 != 11:
        return "год"
    elif 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
        return "года"
    else:
        return "лет"

def plural_reviews(n):
    n = abs(n)
    if n % 10 == 1 and n % 100 != 11:
        return "оценка"
    elif 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
        return "оценки"
    else:
        return "оценок"

class ClientManager:
    @staticmethod
    def show_main_menu(bot, user_id):
        roles = DatabaseManager.get_all_roles(user_id)
        active_role = DatabaseManager.get_active_role(user_id)
        is_admin = DatabaseManager.is_admin(user_id)
        is_barber_filled = DatabaseManager.barber_exists(user_id) if active_role == 'barber' else False

        markup = KeyboardManager.main_menu(
            active_role,
            len(roles),
            is_admin,
            is_barber_filled,
            user_id
        )
        bot.send_message(user_id, "Выберите действие:", reply_markup=markup)

    @staticmethod
    def ask_city(user_id, bot):
        msg = bot.send_message(
            user_id,
            "📍 В каком городе вы хотите искать барбера?",
            reply_markup=types.ReplyKeyboardMarkup(
                resize_keyboard=True
            ).add(types.KeyboardButton("❌ Отмена"))
        )
        bot.register_next_step_handler(msg, ClientManager.handle_city_input, bot)

    @staticmethod
    def handle_city_input(message, bot):
        user_id = message.from_user.id

        if message.text == "❌ Отмена":
            ClientManager.show_main_menu(bot, user_id)
            return

        city_name = message.text.strip()
        city_id = DatabaseManager.get_city_id_by_name(city_name)

        if not city_id:
            msg = bot.send_message(
                user_id,
                f"❌ Город '{city_name}' не найден. Попробуйте ещё раз:",
                reply_markup=types.ReplyKeyboardMarkup(
                    resize_keyboard=True
                ).add(types.KeyboardButton("❌ Отмена"))
            )
            bot.register_next_step_handler(msg, ClientManager.handle_city_input, bot)
            return

        DatabaseManager.save_user_city_selection(user_id, city_id)
        ClientManager.show_active_barbers(bot, user_id, city_id=city_id)

    @staticmethod
    def show_active_barbers(bot, user_id, page=0, city_id=None):
        barbers = DatabaseManager.get_active_barbers(page, city_id=city_id)

        if not barbers:
            bot.send_message(
                user_id,
                "❌ Нет доступных барберов, попробуйте выбрать другой город",
                reply_markup=KeyboardManager.main_menu(
                    DatabaseManager.get_active_role(user_id),
                    len(DatabaseManager.get_all_roles(user_id)),
                    DatabaseManager.is_admin(user_id),
                    DatabaseManager.barber_exists(user_id) if DatabaseManager.get_active_role(user_id) == 'barber' else False,
                    user_id
                )
            )
            return

        markup = types.InlineKeyboardMarkup()

        for barber in barbers:
            btn_text = f"{barber[9]} ({barber[3]})"
            markup.add(types.InlineKeyboardButton(
                btn_text,
                callback_data=f"client_showbarber_{barber[0]}"
            ))

        nav_buttons = []
        if page > 0:
            nav_buttons.append(types.InlineKeyboardButton(
                "⬅️ Назад",
                callback_data=f"client_prev_{page-1}_{city_id if city_id else ''}"
            ))
        if len(barbers) == 10:
            nav_buttons.append(types.InlineKeyboardButton(
                "Вперёд ➡️",
                callback_data=f"client_next_{page+1}_{city_id if city_id else ''}"
            ))

        if nav_buttons:
            markup.row(*nav_buttons)

        markup.add(types.InlineKeyboardButton(
            "⭐ Избранное",
            callback_data="client_show_favorites"
        ))

        markup.add(types.InlineKeyboardButton(
            "🔙 В главное меню",
            callback_data="client_back_to_menu"
        ))

        bot.send_message(
            user_id,
            f"🔍 Доступные барберы (страница {page+1}):",
            reply_markup=markup
        )

    @staticmethod
    def show_favorite_barbers(bot, user_id):
        favorites = DatabaseManager.get_favorite_barbers(user_id)

        if not favorites:
            bot.send_message(
                user_id,
                "⭐ У вас пока нет избранных барберов.",
                reply_markup=KeyboardManager.main_menu(
                    DatabaseManager.get_active_role(user_id),
                    len(DatabaseManager.get_all_roles(user_id)),
                    DatabaseManager.is_admin(user_id),
                    False,
                    user_id
                )
            )
            return

        markup = types.InlineKeyboardMarkup()

        for barber in favorites:
            btn_text = f"{barber['first_name']} ({barber['city_name']})"
            markup.add(types.InlineKeyboardButton(
                btn_text,
                callback_data=f"client_showbarber_{barber['id']}"
            ))

        markup.add(types.InlineKeyboardButton(
            "🔙 В главное меню",
            callback_data="client_back_to_menu"
        ))

        bot.send_message(
            user_id,
            "⭐ Ваши избранные барберы:",
            reply_markup=markup
        )

def register_client_handlers(bot):
    @bot.message_handler(func=lambda msg: msg.text == "⭐ Избранное")
    def handle_favorites(message):
        ClientManager.show_favorite_barbers(bot, message.from_user.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("client_"))
    def handle_client_barber_callback(call):
        user_id = call.from_user.id
        data = call.data

        if data == "client_back_to_menu":
            ClientManager.show_main_menu(bot, user_id)
            bot.answer_callback_query(call.id)
            return

        if data == "client_show_favorites":
            ClientManager.show_favorite_barbers(bot, user_id)
            bot.answer_callback_query(call.id)
            return

        if data.startswith("client_prev_") or data.startswith("client_next_"):
            parts = data.split('_')
            page = int(parts[2])
            city_id = int(parts[3]) if len(parts) > 3 and parts[3] else None
            ClientManager.show_active_barbers(bot, user_id, page=page, city_id=city_id)
            bot.answer_callback_query(call.id)
            return

        elif data.startswith("client_showbarber_"):
            barber_id = int(data.split("_")[2])
            profile = DatabaseManager.get_barber_by_id(barber_id)
            avg_rating, rating_count = DatabaseManager.get_barber_average_rating(barber_id)
            rating_text = f"⭐️ Рейтинг: {avg_rating or 'нет оценок'} ({rating_count} {plural_reviews(rating_count)})\n" if rating_count else "⭐️ Рейтинг: нет оценок\n"

            if profile:
                full_profile = DatabaseManager.get_barber_full_data_by_user_id(profile['user_id'])
                metro_text = f"\n    🚇 Метро: {full_profile['metro_name']}" if full_profile and full_profile.get('metro_name') else ""

                is_favorite = DatabaseManager.is_barber_favorite(user_id, barber_id)

                services = DatabaseManager.get_barber_services(barber_id)
                services_text = "\n💰 Услуги и цены:\n" + "\n".join(
                    [f"• {s[0]}: {s[1]} руб." for s in services]
                ) if services else ""

                description = profile.get('description', '')
                description_text = f"\n📝 Описание: {description}" if description else ""

                years = profile.get('experience_years', 0)
                years_text = f"{years} {plural_years(years)}"

                text = f"""━━━━━━━━━━━━━━━━━━
    👤 Барбер: {profile['first_name']}
    📍 Город: {profile['city_name']} {metro_text}
    💈 Опыт: {years_text}
    {description_text}
    
    {services_text}
    ━━━━━━━━━━━━━━━━━━"""

                markup = types.InlineKeyboardMarkup(row_width=2)
                markup.add(
                    types.InlineKeyboardButton(
                        "📝 Записаться",
                        callback_data=f"client_book_{barber_id}"
                    ),
                    types.InlineKeyboardButton(
                        "⭐ Удалить из избранного" if is_favorite else "⭐ Добавить в избранное",
                        callback_data=f"client_toggle_favorite_{barber_id}"
                    )
                )
                markup.add(types.InlineKeyboardButton(
                    "🔙 Назад к списку",
                    callback_data="client_back_to_list"
                ))
                markup.add(types.InlineKeyboardButton(
                    "🏠 В главное меню",
                    callback_data="client_back_to_menu"
                ))

                photos = DatabaseManager.get_barber_photos(profile['id'])
                if photos:
                    try:
                        media = []
                        for idx, photo in enumerate(photos):
                            if idx == 0:
                                media.append(types.InputMediaPhoto(photo[0], caption=text))
                            else:
                                media.append(types.InputMediaPhoto(photo[0]))
                        bot.send_media_group(user_id, media)
                        bot.send_message(user_id, "Выберите действие:", reply_markup=markup)
                    except Exception:
                        bot.send_message(user_id, text, reply_markup=markup)
                else:
                    bot.send_message(user_id, text, reply_markup=markup)
            else:
                bot.send_message(user_id, "❌ Анкета не найдена.")
            bot.answer_callback_query(call.id)
            return

        elif data == "client_back_to_list":
            city_id = DatabaseManager.get_user_city_selection(user_id)
            ClientManager.show_active_barbers(bot, user_id, city_id=city_id)
            bot.answer_callback_query(call.id)
            return

        elif data.startswith("client_book_"):
            barber_id = int(data.split("_")[2])
            profile = DatabaseManager.get_barber_by_id(barber_id)

            if profile:
                contacts_text = f"""📱 Контакты барбера:
    • Instagram: {profile['instagram'] or 'не указан'}
    • WhatsApp: {profile['whatsapp'] or 'не указан'}
    • Telegram: {profile['telegram'] or 'не указан'}
    
    Свяжитесь с барбером для записи!"""

                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton(
                    "🔙 Назад к анкете",
                    callback_data=f"client_showbarber_{barber_id}"
                ))

                bot.send_message(
                    user_id,
                    contacts_text,
                    reply_markup=markup
                )
            else:
                bot.send_message(user_id, "❌ Барбер не найден")
            bot.answer_callback_query(call.id)
            return

        elif data.startswith("client_toggle_favorite_"):
            barber_id = int(data.split("_")[3])
            was_favorite = DatabaseManager.is_barber_favorite(user_id, barber_id)
            success = DatabaseManager.toggle_favorite(user_id, barber_id)

            if success:
                action = "удален из избранного" if was_favorite else "добавлен в избранное"
                bot.answer_callback_query(
                    call.id,
                    f"✅ Барбер {action}",
                    show_alert=True
                )

                try:
                    if was_favorite:
                        new_text = "⭐ Добавить в избранное"
                    else:
                        new_text = "⭐ Удалить из избранного"

                    markup = types.InlineKeyboardMarkup(row_width=2)
                    markup.add(
                        types.InlineKeyboardButton(
                            "📝 Записаться",
                            callback_data=f"client_book_{barber_id}"
                        ),
                        types.InlineKeyboardButton(
                            new_text,
                            callback_data=f"client_toggle_favorite_{barber_id}"
                        )
                    )
                    markup.add(types.InlineKeyboardButton(
                        "🔙 Назад к списку",
                        callback_data="client_back_to_list"
                    ))
                    markup.add(types.InlineKeyboardButton(
                        "🏠 В главное меню",
                        callback_data="client_back_to_menu"
                    ))

                    bot.edit_message_reply_markup(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        reply_markup=markup
                    )
                except Exception as e:
                    print(f"Ошибка при обновлении кнопки: {e}")
            else:
                bot.answer_callback_query(call.id, "❌ Ошибка при изменении избранного")
            return

    @bot.callback_query_handler(func=lambda call: call.data == "client_back_to_search")
    def handle_back_to_search(call):
        user_id = call.from_user.id
        city_id = DatabaseManager.get_user_city_selection(user_id)
        ClientManager.show_active_barbers(bot, user_id, city_id=city_id)
        bot.answer_callback_query(call.id)