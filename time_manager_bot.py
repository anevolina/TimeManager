# -*- coding: utf-8 -*-
import os
import redis
import time
import threading

from dotenv import load_dotenv
from os.path import join, dirname
from bot_answers import TimeManagerBot
from datetime import datetime, timedelta
from collections import deque


from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters

from single_timer import load_backup as load_single_timers
from notificator import send_update_notification

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

#Initialize database for timers settings
timers_settings = redis.Redis(db=2)

# Choose language buttons
lang_buttons = [[InlineKeyboardButton("Русский", callback_data='RU'),
                InlineKeyboardButton("English", callback_data='EN')]]


# Dynamic control buttons
def get_keyboard_buttons(status, language, chat_id=None):
    """ Status could be:
    start - to start current timer
    pause - to pause current timer
    10more - to extend current timer for add_more minutes (parameter from settings)
    10confirm - to confirm extending for timers - happens after 3 extends in a row
    """

    if language == 'EN':
        if status == 'start':
            text1 = '▶ Start '
            callback_data1 = 'start'
        elif status == 'pause':
            text1 = '⌛  Pause'
            callback_data1 = 'pause'
        elif status == '10confirm':
            text1 = '💯 confirm'
            callback_data1 = '10confirm'
        else:
            text1 = '🕝 Gimme more'
            callback_data1 = '10more'

        if bot_collection[chat_id] and not bot_collection[chat_id].timers.scheduled_bunch:
            text2 = '🔄 Repeat'
            callback_data2 = 'repeat'
        else:
            text2 = '⏩ Next'
            callback_data2 = 'next'

        text3 = '❓ How much left?'
    else:
        if status == 'start':
            text1 = '▶  Старт'
            callback_data1 = 'start'
        elif status == 'pause':
            text1 = '⌛ Пауза'
            callback_data1 = 'pause'
        elif status == '10confirm':
            text1 = '💯 все ок'
            callback_data1 = '10confirm'
        else:
            text1 = '🕝  Добавь еще!'
            callback_data1 = '10more'

        if bot_collection[chat_id] and not bot_collection[chat_id].timers.scheduled_bunch:
            text2 = '🔄  Повтори'
            callback_data2 = 'repeat'
        else:
            text2 = '⏩ Дальше'
            callback_data2 = 'next'

        text3 = '❓ Сколько осталось?'


    control_buttons = [[InlineKeyboardButton(text1, callback_data=callback_data1),
                        InlineKeyboardButton(text2, callback_data=callback_data2)],
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

    if user_id not in bot_collection:
        existed = try_load(user_id)

        if not existed:
            start_callback(bot, update)
            return

    message = bot_collection[user_id].get_help_message()

    bot.send_message(chat_id=update.message.chat_id, text=message, parse_mode=ParseMode.MARKDOWN)


# define reaction to /settings command in tlgr
def settings_callback(bot, update):

    user_id = check_user(bot, update)

    if user_id:

        message = bot_collection[user_id].get_settings_message()
        bot.send_message(chat_id=update.message.chat_id, text=message)


# define reaction to /language command in tlgr
def language_callback(bot, update):

    user_id = update.message.from_user.id

    settings_update[user_id] = 'lang'
    start_callback(bot, update)


# define reaction to /alarm_count command in tlgr
def alarm_count_callback(bot, update):

    user_id = check_user(bot, update)

    if user_id:

        settings_update[user_id] = 'alarm_count'
        message = bot_collection[user_id].get_set_alarm_count_message()
        bot.send_message(chat_id=user_id, text=message)


# define reaction to /alarm_message command in tlgr
def alarm_message_callback(bot, update):

    user_id = check_user(bot, update)

    if user_id:

        settings_update[user_id] = 'alarm_message'
        message = bot_collection[user_id].get_set_alarm_message_message()
        bot.send_message(chat_id=user_id, text=message)


# define reaction to /add_more command in tlgr
def add_more_callback(bot, update):
    user_id = check_user(bot, update)

    if user_id:

        settings_update[user_id] = 'add_more'
        message = bot_collection[user_id].get_set_add_more_message()
        bot.send_message(chat_id=user_id, text=message)


# define reaction to /cancel command in tlgr
def cancel_callback(bot, update):

    user_id = check_user(bot, update)

    if user_id:
        settings_update.pop(user_id)
        message = bot_collection[user_id].get_cancel_message()
        bot.send_message(chat_id=user_id, text=message)


# define reaction to /auto_start command in tlgr
def auto_start_callback(bot, update):
    user_id = check_user(bot, update)

    if user_id:

        bot_collection[user_id].auto_start = not bot_collection[user_id].auto_start

        message = bot_collection[user_id].get_set_auto_start_message()
        bot.send_message(chat_id=user_id, text=message)


# ----------------------------------------------
# reaction for simple message
# ----------------------------------------------


def message_answer(bot, update):
    user_id = check_user(bot, update)

    if user_id:

        bot_message, timer_on, prev_message = bot_collection[user_id].check_user_message(bot, update, settings_update)

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
            bot_collection[chat_id].save_settings(set_update)
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

    elif query.data == 'repeat':
        repeat_timers(bot, chat_id, message_id)

# ----------------------------------------------
# work functions
# ----------------------------------------------


def start_bot(user_id, lang, bot, message_id):
    """Start bot and add it into collection"""


    bot_collection[user_id] = TimeManagerBot(user_id, lang)
    message = bot_collection[user_id].get_help_message()
    bot_collection[user_id].save_settings(set_update='ALL')

    bot.edit_message_text(text=message, chat_id=user_id, message_id=message_id)


def start_timer(bot, chat_id, message_id, extended=False):
    """ Start every new timer. If previous timer was paused, started for the remain amount of time"""

    next_func = update_timer(bot, chat_id, message_id)
    result = bot_collection[chat_id].start_timer(next_func)
    bot_collection[chat_id].paused = False

    if not extended:
        bot_collection[chat_id].how_many_extended = 0

    if result:
        keyboard_buttons = get_keyboard_buttons('pause', bot_collection[chat_id].lang, chat_id)
        reply_markup = InlineKeyboardMarkup(keyboard_buttons)
        message = bot_collection[chat_id].get_started_timer_message()
        try:
            bot.edit_message_text(text=message, chat_id=chat_id, message_id=message_id, reply_markup=reply_markup)

        except:
            pass

    save_timers(chat_id)


def pause_timer(bot, chat_id, message_id):
    """ Pause timer and save remain time"""

    bot_collection[chat_id].timers.current_timer.cancel()

    remain = remain_time(chat_id)

    bot_collection[chat_id].timers.extended = remain
    bot_collection[chat_id].paused = True

    message = bot_collection[chat_id].get_paused_timer_message()
    keyboard_buttons = get_keyboard_buttons('start', bot_collection[chat_id].lang, chat_id)
    reply_markup = InlineKeyboardMarkup(keyboard_buttons)

    bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=message, reply_markup=reply_markup)

    save_timers(chat_id)


def next_timer(bot, chat_id, message_id):
    """Set to zero all additional settings, and start next timer"""

    bot_collection[chat_id].timers.current_timer.cancel()
    bot_settings_set_nul(chat_id)

    start_timer(bot, chat_id, message_id)


def add_more_timer(bot, chat_id, message_id, confirm=False):
    """ Ask to confirm every extension after 3 times in a row"""

    if bot_collection[chat_id].how_many_extended >= 3 and not confirm:
        message = bot_collection[chat_id].get_confirm_message()
        keyboard_buttons = get_keyboard_buttons('10confirm', bot_collection[chat_id].lang, chat_id)
        reply_markup = InlineKeyboardMarkup(keyboard_buttons)

        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=message, reply_markup=reply_markup)

    else:
        bot_collection[chat_id].how_many_extended += 1
        bot_collection[chat_id].timers.extended = bot_collection[chat_id].add_more
        bot_collection[chat_id].timers.additional_time = True
        start_timer(bot, chat_id, message_id, extended=True)


def check_status(bot, chat_id, query):
    """Check how many minutes remain for current timer"""

    remain = remain_time(chat_id)
    query_id = query.id

    message = bot_collection[chat_id].get_remained_message(remain)

    bot.answer_callback_query(callback_query_id=query_id, text=message)

    pass


def set_old_timers_message(bot, chat_id, message_id):
    """ Delete buttons for the last set of timers"""

    message = bot_collection[chat_id].get_old_timers_message()

    bot.edit_message_text(text=message, chat_id=chat_id, message_id=message_id)


def bot_settings_set_nul(chat_id):
    """Set to null additional settings for a timer"""

    bot_collection[chat_id].timers.extended = 0
    bot_collection[chat_id].timers.additional_time = False
    bot_collection[chat_id].timers.current_time = 0
    bot_collection[chat_id].paused = False

    save_timers(chat_id)


def update_timer(bot, user_id, message_id):
    """Function called after finishing every timer"""

    def finish_timer():
        keyboard_buttons = get_keyboard_buttons('extend', bot_collection[user_id].lang, user_id)
        reply_markup = InlineKeyboardMarkup(keyboard_buttons)
        message = bot_collection[user_id].get_finished_timer_message()

        try:
            bot.edit_message_text(text=message, chat_id=user_id, message_id=message_id, reply_markup=reply_markup)
        except:
            pass

        bot_settings_set_nul(user_id)

        alarm = alarm_message(bot, user_id)
        alarm_thread = threading.Timer(0, alarm)
        alarm_thread.start()

    return finish_timer


def alarm_message(bot, user_id):
    """Function to send and delete messages like alarm"""

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
    """Converting delta datetime to minutes"""

    minutes = time_passed.seconds // 60

    return minutes


def try_load(user_id):
    """Try to load settings for current user"""

    settings = redis.Redis(db=1)

    if str(user_id).encode() in settings.keys():
        bot_collection[user_id] = TimeManagerBot(user_id, 'EN')
        bot_collection[user_id].load_settings()
        return True

    return False



def remain_time(chat_id):
    """Return how many time left for current timer"""

    if bot_collection[chat_id].paused:
        return bot_collection[chat_id].timers.extended

    current_time = datetime.now()
    time_passed = convert_time(current_time - bot_collection[chat_id].last_timer_start)
    time_was = bot_collection[chat_id].timers.current_time
    remain = time_was - time_passed

    return remain if remain > 0 else 0

def repeat_timers(bot, chat_id, message_id):
    """Repeat whole bunch of the last timers"""

    bot_collection[chat_id].timers.repeat()
    start_timer(bot, chat_id, message_id)

def check_user(bot, update):
    user_id = update.message.from_user.id

    if user_id not in bot_collection:
        existed = try_load(user_id)

        if not existed:
            start_callback(bot, update)
            return False

    return user_id

def save_timers(user_id):
    """Save current timers settings for a user"""

    timers_settings.hmset(user_id, {
        'last_timer_start': bot_collection[user_id].last_timer_start.isoformat(),
        'message_id': bot_collection[user_id].message_id,
        'how_many_extended': bot_collection[user_id].how_many_extended,
        'paused': int(bot_collection[user_id].paused),

        'scheduled_bunch': '-'.join([str(i) for i in list(bot_collection[user_id].timers.scheduled_bunch)]),
        'prev_bunch': '-'.join([str(i) for i in list(bot_collection[user_id].timers.prev_bunch)]),

        'extended': bot_collection[user_id].timers.extended,
        'additional_time': int(bot_collection[user_id].timers.additional_time),
        'current_time': bot_collection[user_id].timers.current_time

    })


def load_timers(bot):
    """load all timers for current users"""

    load_single_timers(bot)

    all_users = timers_settings.keys('*')

    for user in all_users:
        user_id = int(user)

        current_timer_minutes = int(timers_settings.hget(user_id, 'current_time').decode())
        scheduled_bunch = timers_settings.hget(user_id, 'scheduled_bunch').decode()
        message_id = int(timers_settings.hget(user_id, 'message_id').decode())

        if current_timer_minutes == 0 and not scheduled_bunch:
            message = 'Current timers were turned off due to inactivity\n\n' \
                      'Текущие таймеры были отключены в связи с неактивностью'

            try:
                bot.edit_message_text(text=message, chat_id=user_id, message_id=message_id)
                timers_settings.delete(user)

            except:
                pass

            continue

        bot_collection[user_id] = TimeManagerBot(user_id, 'EN')
        bot_collection[user_id].load_settings()

        bot_collection[user_id].message_id = message_id
        bot_collection[user_id].paused = bool(int(timers_settings.hget(user_id, 'paused').decode()))
        bot_collection[user_id].timers.additional_time = bool(int(timers_settings.hget(user_id, 'additional_time').decode()))
        bot_collection[user_id].how_many_extended = int(timers_settings.hget(user_id, 'how_many_extended').decode())
        bot_collection[user_id].timers.extended = int(timers_settings.hget(user_id, 'extended').decode())


        if scheduled_bunch:
            bot_collection[user_id].timers.scheduled_bunch = deque([int(i) for i in scheduled_bunch.split('-')])

        prev_bunch = timers_settings.hget(user_id, 'prev_bunch').decode()

        if prev_bunch:
            bot_collection[user_id].timers.prev_bunch = deque([int(i) for i in prev_bunch.split('-')])

        if current_timer_minutes and not bot_collection[user_id].paused:
            last_timer_start = datetime.fromisoformat(timers_settings.hget(user_id, 'last_timer_start').decode())
            bot_collection[user_id].last_timer_start = last_timer_start

            last_timer_end = last_timer_start + timedelta(minutes=int(current_timer_minutes))
            current_time = datetime.now()

            remain_time = last_timer_end - current_time
            remain_minutes = convert_time(remain_time)

            if remain_time.days < 0 or  remain_minutes == 0:
                # Change message, ring alarm
                bot_collection[user_id].timers.current_time = current_timer_minutes
                update_timer(bot, user_id, message_id)()

            else:
                # Start timer with remain time
                bot_collection[user_id].timers.extended = remain_minutes
                start_timer(bot, user_id, message_id)


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

load_timers(updater.bot)

#Send notification about updates etc.

send_update_notification(updater.bot, 1)