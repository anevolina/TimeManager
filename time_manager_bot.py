from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters
from dotenv import load_dotenv
import os
from os.path import join, dirname
from bot_answers import TimeManagerBot
import time
import threading
from datetime import datetime

# ----------------------------------------------
# Initializing
# ----------------------------------------------

# Load .env & token for the bot
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)
TLGR_TOKEN = os.environ.get('TLGR_TOKEN')

# Initialize updater and dispatcher
updater = Updater(token=TLGR_TOKEN)
dispatcher = updater.dispatcher

# Initialize bot collection for dividing it by chats
bot_collection = {}
settings_update = {}

# Choose language buttons
lang_buttons = [[InlineKeyboardButton("Русский", callback_data='RU'),
                InlineKeyboardButton("English", callback_data='EN')]]


# Dynamic control buttons
def get_keyboard_buttons(status, language, chat_id=None):
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
        elif status == '10confirm':
            text1 = '💯 sure 💯'
            callback_data = '10confirm'
        else:
            text1 = 'Give me more minutes  🤓'
            callback_data = '10more'

        if bot_collection[chat_id] and not bot_collection[chat_id].timers.scheduled_bunch:
            text2 = 'No more timers'
        else:
            text2 = 'Next  ⏩'

        text3 = 'how much left?'
    else:
        if status == 'start':
            text1 = 'Старт ▶'
            callback_data = 'start'
        elif status == 'pause':
            text1 = 'Останови ⌛'
            callback_data = 'pause'
        elif status == '10confirm':
            text1 = '💯 все ок 💯'
            callback_data = '10confirm'
        else:
            text1 = 'Мне нужно еще время!  🤓'
            callback_data = '10more'

        if bot_collection[chat_id] and not bot_collection[chat_id].timers.scheduled_bunch:
            text2 = 'Таймеров больше нет'
        else:
            text2 = 'Дальше  ⏩'

        text3 = 'сколько осталось?'


    control_buttons = [[InlineKeyboardButton(text1, callback_data=callback_data),
                        InlineKeyboardButton(text2, callback_data='next')],
                       [InlineKeyboardButton(text3, callback_data='status')]]

    return control_buttons


# ----------------------------------------------
# user functions, started from '/'
# ----------------------------------------------

# define reaction to /start command in tlgr
def start_callback(bot, update):
    reply_markup = InlineKeyboardMarkup(lang_buttons)
    update.message.reply_text("Выбери язык | Choose language", reply_markup=reply_markup)


# define reaction to /help command in tlgr
def help_callback(bot, update):
    user_id = update.message.from_user.id

    if user_id in bot_collection:
        message = bot_collection[user_id].get_help_message()
        bot.send_message(chat_id=update.message.chat_id, text=message)
    else:
        start_callback(bot, update)


# define reaction to /settings command in tlgr
def settings_callback(bot, update):
    user_id = update.message.from_user.id

    if user_id in bot_collection:
        message = bot_collection[user_id].get_settings_message()
        bot.send_message(chat_id=update.message.chat_id, text=message)
    else:
        start_callback(bot, update)


# define reaction to /language command in tlgr
def language_callback(bot, update):
    user_id = update.message.from_user.id

    settings_update[user_id] = 'language'
    start_callback(bot, update)


# define reaction to /alarm_count command in tlgr
def alarm_count_callback(bot, update):
    user_id = update.message.from_user.id

    settings_update[user_id] = 'alarm_count'
    message = bot_collection[user_id].get_set_alarm_count_message()
    bot.send_message(chat_id=user_id, text=message)


# define reaction to /alarm_message command in tlgr
def alarm_message_callback(bot, update):
    user_id = update.message.from_user.id

    settings_update[user_id] = 'alarm_message'
    message = bot_collection[user_id].get_set_alarm_message_message()
    bot.send_message(chat_id=user_id, text=message)


# define reaction to /add_more command in tlgr
def add_more_callback(bot, update):
    user_id = update.message.from_user.id

    settings_update[user_id] = 'add_more'
    message = bot_collection[user_id].get_set_add_more_message()
    bot.send_message(chat_id=user_id, text=message)


# define reaction to /cancel command in tlgr
def cancel_callback(bot, update):
    user_id = update.message.from_user.id

    settings_update.pop(user_id)
    message = bot_collection[user_id].get_cancel_message()
    bot.send_message(chat_id=user_id, text=message)


# define reaction to /auto_start command in tlgr
def auto_start_callback(bot, update):
    user_id = update.message.from_user.id

    bot_collection[user_id].auto_start = not bot_collection[user_id].auto_start

    message = bot_collection[user_id].get_set_auto_start_message()
    bot.send_message(chat_id=user_id, text=message)

# ----------------------------------------------
# reaction for simple message
# ----------------------------------------------


def message_answer(bot, update):
    user_id = update.message.from_user.id

    if user_id not in bot_collection:
        start_callback(bot, update)
        return

    user_message = update.message.text.strip()

    bot_message, timer_on, prev_message = bot_collection[user_id].check_callbak(user_message, settings_update, user_id)

    if not bot_message:
        return

    bot.send_message(chat_id=user_id, text=bot_message)

    if timer_on and not bot_collection[user_id].auto_start:
        bot_message = bot_collection[user_id].get_current_timer_message()
        reply_markup = InlineKeyboardMarkup(get_keyboard_buttons('start', bot_collection[user_id].lang, user_id))
        sent_message = bot.send_message(chat_id=user_id, text=bot_message, reply_markup=reply_markup)
        bot_collection[user_id].message_id = sent_message.message_id

    elif timer_on and bot_collection[user_id].auto_start:
        sent_message = bot.send_message(chat_id=user_id, text='First timer is about to start')
        bot_collection[user_id].message_id = sent_message.message_id
        start_timer(bot, user_id, sent_message.message_id)

    if prev_message:
        set_old_timers_message(bot, user_id, prev_message)


# ----------------------------------------------
# reaction for callback buttons
# ----------------------------------------------

def callback_answer(bot, update):
    query = update.callback_query
    chat_id = query.message.chat_id
    message_id = query.message.message_id

    if query.data in ['RU', 'EN']:
        set_update = settings_update.get(chat_id)

        if set_update:
            assert bot_collection[chat_id], "Houston we've got a problem"
            bot_collection[chat_id].lang = query.data
            message = bot_collection[chat_id].get_updated_language_message()
            bot.edit_message_text(text=message, chat_id=chat_id, message_id=message_id)
            settings_update.pop(chat_id)

        else:
            start_bot(chat_id, query.data, bot, message_id)

    elif query.data == 'start':
        start_timer(bot, chat_id, message_id)

    elif query.data == 'pause':
        pause_timer(bot, chat_id, message_id)

    elif query.data == 'next':
        next_timer(bot, chat_id, message_id)

    elif query.data == '10more':
        add_more_timer(bot, chat_id, message_id)

    elif query.data == '10confirm':
        add_more_timer(bot, chat_id, message_id, confirm=True)
    elif query.data == 'status':
        check_status(bot, chat_id, query)

# ----------------------------------------------
# work functions
# ----------------------------------------------


def start_bot(user_id, lang, bot, message_id):

    bot_collection[user_id] = TimeManagerBot(user_id, lang)
    message = bot_collection[user_id].get_help_message()


    bot.edit_message_text(text=message, chat_id=user_id, message_id=message_id)


def start_timer(bot, chat_id, message_id, extended=False):
    next_func = update_timer(bot, chat_id, message_id)
    result = bot_collection[chat_id].start_timer(next_func)

    if not extended:
        bot_collection[chat_id].extended10 = 0

    if result:
        keyboard_buttons = get_keyboard_buttons('pause', bot_collection[chat_id].lang, chat_id)
        reply_markup = InlineKeyboardMarkup(keyboard_buttons)
        message = bot_collection[chat_id].get_started_timer_message()
        bot.edit_message_text(text=message, chat_id=chat_id, message_id=message_id, reply_markup=reply_markup)


def pause_timer(bot, chat_id, message_id):
   bot_collection[chat_id].timers.current_timer.cancel()

   remain = remain_time(chat_id)

   bot_collection[chat_id].timers.extended = remain

   message = bot_collection[chat_id].get_paused_timer_message()
   keyboard_buttons = get_keyboard_buttons('start', bot_collection[chat_id].lang, chat_id)
   reply_markup = InlineKeyboardMarkup(keyboard_buttons)

   bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=message, reply_markup=reply_markup)


def next_timer(bot, chat_id, message_id):
    bot_collection[chat_id].timers.current_timer.cancel()
    bot_settings_set_nul(chat_id)

    start_timer(bot, chat_id, message_id)


def add_more_timer(bot, chat_id, message_id, confirm=False):

    if bot_collection[chat_id].extended10 >= 3 and not confirm:
        message = bot_collection[chat_id].get_confirm_message()
        keyboard_buttons = get_keyboard_buttons('10confirm', bot_collection[chat_id].lang, chat_id)
        reply_markup = InlineKeyboardMarkup(keyboard_buttons)

        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=message, reply_markup=reply_markup)

    else:
        bot_collection[chat_id].extended10 += 1
        bot_collection[chat_id].timers.extended = bot_collection[chat_id].add_more
        bot_collection[chat_id].timers.additional_time = True
        start_timer(bot, chat_id, message_id, extended=True)


def check_status(bot, chat_id, query):
    remain = remain_time(chat_id)
    query_id = query.id

    message = bot_collection[chat_id].get_remained_message(remain)

    bot.answer_callback_query(callback_query_id=query_id, text=message)

    pass


def set_old_timers_message(bot, chat_id, message_id):

    message = bot_collection[chat_id].get_old_timers_message()

    bot.edit_message_text(text=message, chat_id=chat_id, message_id=message_id)


def bot_settings_set_nul(chat_id):

    bot_collection[chat_id].timers.extended = 0
    bot_collection[chat_id].timers.additional_time = False


def update_timer(bot, user_id, message_id):
    def finish_timer():
        keyboard_buttons = get_keyboard_buttons('extend', bot_collection[user_id].lang, user_id)
        reply_markup = InlineKeyboardMarkup(keyboard_buttons)
        message = bot_collection[user_id].get_finished_timer_message()
        bot.edit_message_text(text=message, chat_id=user_id, message_id=message_id, reply_markup=reply_markup)
        bot_settings_set_nul(user_id)

        alarm = alarm_message(bot, user_id)
        alarm_thread = threading.Timer(0, alarm)
        alarm_thread.start()

    return finish_timer


def alarm_message(bot, user_id):
    def ring_alarm():

        message = bot_collection[user_id].get_alarm_message()
        alarm_count = bot_collection[user_id].alarm_count

        for i in range(alarm_count):
            bot_message = bot.send_message(text=message, chat_id=user_id)
            time.sleep(1)
            message_id = bot_message.message_id
            bot.delete_message(chat_id=user_id, message_id=message_id)

    return ring_alarm


def convert_time(time_passed):
    minutes = time_passed.seconds // 60

    return minutes


def remain_time(chat_id):
    current_time = datetime.now()
    time_passed = convert_time(current_time - bot_collection[chat_id].last_timer_start)
    time_was = bot_collection[chat_id].timers.current_time
    remain = time_was - time_passed

    return remain if remain > 0 else 0


# define command handlers
start_handler = CommandHandler("start", start_callback)
help_handler = CommandHandler("help", help_callback)
settings_handler = CommandHandler("settings", settings_callback)
language_handler = CommandHandler("language", language_callback)
alarm_count_handler = CommandHandler('alarm_count', alarm_count_callback)
alarm_message_handler = CommandHandler('alarm_message', alarm_message_callback)
add_more_handler = CommandHandler('add_more', add_more_callback)
cancel_handler = CommandHandler('cancel', cancel_callback)
auto_start_handler = CommandHandler('auto_start', auto_start_callback)

# define other handlers
callback_handler = CallbackQueryHandler(callback_answer)
message_handler = MessageHandler(Filters.text, message_answer)


# adding command handlers to our dispatcher
dispatcher.add_handler(start_handler)
dispatcher.add_handler(help_handler)
dispatcher.add_handler(settings_handler)
dispatcher.add_handler(language_handler)
dispatcher.add_handler(alarm_count_handler)
dispatcher.add_handler(alarm_message_handler)
dispatcher.add_handler(add_more_handler)
dispatcher.add_handler(cancel_handler)
dispatcher.add_handler(auto_start_handler)

# adding other handlers to our dispatcher
dispatcher.add_handler(callback_handler)
dispatcher.add_handler(message_handler)

# and start the bot...
updater.start_polling()
