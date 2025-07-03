from telebot import types
from managers.database import DatabaseManager
from managers.keyboard import KeyboardManager
from config.constants import HAIRCUT_TYPES

class GuideManager:
    @staticmethod
    def show_categories(bot, chat_id):
        markup = KeyboardManager.get_guide_categories()
        bot.send_message(
            chat_id,
            "📚 Выберите категорию стрижек:",
            reply_markup=markup
        )

    @staticmethod
    def show_haircuts(bot, chat_id, category_type):
        category_id = DatabaseManager.get_category_id_by_type(category_type)
        if not category_id:
            return bot.send_message(chat_id, "❌ Категория не найдена")

        haircuts = DatabaseManager.get_haircuts_by_category(category_id)
        if not haircuts:
            return bot.send_message(chat_id, "❌ В этой категории пока нет стрижек")

        markup = KeyboardManager.get_haircuts_keyboard(haircuts)
        bot.send_message(
            chat_id,
            f"✂️ Выберите стрижку из категории '{HAIRCUT_TYPES.get(category_type, '')}':",
            reply_markup=markup
        )

    @staticmethod
    def show_haircut_details(bot, chat_id, haircut_id):
        haircut = DatabaseManager.get_haircut_details(haircut_id)
        if not haircut:
            return bot.send_message(chat_id, "❌ Стрижка не найдена")

        photos = DatabaseManager.get_haircut_photos(haircut_id)
        text = (
            f"✂️ <b>{haircut['name']}</b>\n\n"
           
            f"<b>Советы по укладке:</b>\n{haircut['styling_tips'] or 'Нет советов'}"
        )

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(
            "🔙 Назад",
            callback_data=f"guide_category_{haircut['category_type']}"
        ))

        if photos:
            try:
                media = [types.InputMediaPhoto(photos[0][0], caption=text, parse_mode='HTML')]
                for photo in photos[1:]:
                    media.append(types.InputMediaPhoto(photo[0]))
                bot.send_media_group(chat_id, media)
                bot.send_message(chat_id, "Выберите действие:", reply_markup=markup)
            except Exception as e:
                print(f"Ошибка отправки фото: {e}")
                bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')
        else:
            bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')

    @staticmethod
    def init_handlers(bot):
        @bot.message_handler(func=lambda msg: msg.text == "📚 Справочник")
        def handle_guide(message):
            GuideManager.show_categories(bot, message.chat.id)

        @bot.callback_query_handler(func=lambda call: call.data.startswith("guide_"))
        def handle_guide_callback(call):
            if call.data.startswith("guide_category_"):
                category_type = call.data.split("_")[2]
                GuideManager.show_haircuts(bot, call.message.chat.id, category_type)
            elif call.data.startswith("guide_haircut_"):
                haircut_id = int(call.data.split("_")[2])
                GuideManager.show_haircut_details(bot, call.message.chat.id, haircut_id)
            elif call.data == "guide_back_to_categories":
                GuideManager.show_categories(bot, call.message.chat.id)
            bot.answer_callback_query(call.id)