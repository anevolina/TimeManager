from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters
from dotenv import load_dotenv
import os
from os.path import join, dirname
from bot_answers import TimeManagerBot
import time
import threading


# Load .env & token for the bot
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)
TLGR_TOKEN = os.environ.get('TLGR_TOKEN')

# Initialize updater and dispatcher
updater = Updater(token=TLGR_TOKEN)
dispatcher = updater.dispatcher

# Initialize bot collection for dividing it by chats
bot_collection = {}

# Choose language buttons
lang_buttons = [[InlineKeyboardButton("Русский", callback_data='RU'),
                InlineKeyboardButton("English", callback_data='EN')]]

# Dynamic control buttons
def get_keyboard_buttons(status, language):
    """ Status could be:
    start - to start current timer
    pause - to pause current timer
    extend - to extend currennt timer for 5 mins
    """

    if language == 'EN':
        if status == 'start':
            text1 = 'Start  ▶'
            callback_data = 'start'
        elif status == 'pause':
            text1 = 'Pause  ⌛'
            callback_data = 'pause'
        else:
            text1 = 'Give me 10 min more  💃'
            callback_data = '10more'

        text2 = 'Next  ⏩'
    else:
        if status == 'start':
            text1 = 'Запускай ▶'
            callback_data = 'start'
        elif status == 'pause':
            text1 = 'Останови ⌛'
            callback_data = 'pause'
        else:
            text1 = 'Давай еще 10 минут  💃'
            callback_data = '10more'

        text2 = 'Дальше  ⏩'

    control_buttons = [[InlineKeyboardButton(text1, callback_data=callback_data),
                        InlineKeyboardButton(text2, callback_data='next')]]

    return control_buttons


# define reaction to /start command in tlgr
def start_callback(bot, update):
    reply_markup = InlineKeyboardMarkup(lang_buttons)
    update.message.reply_text("Выбери язык | Choose language", reply_markup=reply_markup)

# define reaction to /help command in tlgr
def help_callback(bot, update):
    user_id = update.message.from_user.id

    if user_id in bot_collection:
        message = bot_collection[user_id].get_help()
        bot.send_message(chat_id=update.message.chat_id, text=message)
    else:
        start_callback(bot, update)


def callback_answer(bot, update):
    query = update.callback_query
    chat_id = query.message.chat_id
    message_id = query.message.message_id

    if query.data in ['RU', 'EN']:
        start_bot(chat_id, query.data)
        message = bot_collection[chat_id].get_help()
        bot.edit_message_text(text=message, chat_id=chat_id, message_id=message_id)

    elif query.data == 'start':
        next_func = update_timer(bot, chat_id, message_id)
        result = bot_collection[chat_id].start_timer(next_func)

        if result:
            keyboard_buttons = get_keyboard_buttons('pause', bot_collection[chat_id].lang)
            reply_markup = InlineKeyboardMarkup(keyboard_buttons)
            message = bot_collection[chat_id].get_pause_timer_message()
            bot.edit_message_text(text=message, chat_id=chat_id, message_id=message_id, reply_markup=reply_markup)

    elif query.data == 'pause':
        pass
    elif query.data == 'next':
        pass
    elif query.data == '10more':
        pass



def message_answer(bot, update):
    user_id = update.message.from_user.id

    if user_id not in bot_collection:
        start_callback(bot, update)
        return

    user_message = update.message.text.strip()

    bot_message, timer_on = bot_collection[user_id].check_callbak(user_message)

    if not bot_message:
        return

    bot.send_message(chat_id=user_id, text=bot_message)

    if timer_on:
        bot_message = bot_collection[user_id].get_current_timer_message()
        reply_markup = InlineKeyboardMarkup(get_keyboard_buttons('start', bot_collection[user_id].lang))
        bot.send_message(chat_id=user_id, text=bot_message, reply_markup=reply_markup)


def start_bot(user_id, lang):
    bot_collection[user_id] = TimeManagerBot(user_id, lang)


def update_timer(bot, user_id, message_id):
    def finish_timer():
        keyboard_buttons = get_keyboard_buttons('extend', bot_collection[user_id].lang)
        reply_markup = InlineKeyboardMarkup(keyboard_buttons)
        message = bot_collection[user_id].get_finished_timer_message()
        bot.edit_message_text(text=message, chat_id=user_id, message_id=message_id, reply_markup=reply_markup)

        alarm = alarm_message(bot, user_id)
        alarm_thread = threading.Timer(0, alarm)
        alarm_thread.start()

    return finish_timer

def alarm_message(bot, user_id):
    def ring_alarm():

        message = bot_collection[user_id].get_alarm_message()

        for i in range(5):
            bot_message = bot.send_message(text=message, chat_id=user_id)
            time.sleep(1)
            message_id = bot_message.message_id
            bot.delete_message(chat_id=user_id, message_id=message_id)

    return ring_alarm


# define all handlers
start_handler = CommandHandler("start", start_callback)
help_handler = CommandHandler("help", help_callback)
callback_handler = CallbackQueryHandler(callback_answer)
message_handler = MessageHandler(Filters.text, message_answer)


# adding handlers to our dispatcher
dispatcher.add_handler(start_handler)
dispatcher.add_handler(help_handler)
dispatcher.add_handler(callback_handler)
dispatcher.add_handler(message_handler)

# and start the bot...
updater.start_polling()