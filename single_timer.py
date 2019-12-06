"""
 На вход подается  bot, update

"""
import re
import redis
import threading

from datetime import datetime, timedelta

backup = redis.Redis(db=3)


def start_single_timer(bot, lang, count, user_id, attrs):
    minutes = int(attrs[0][0])
    message = ' '. join(attrs[1])

    key = save_backup(user_id, minutes, message, count)
    start_timer(bot, message, user_id, count, key, minutes)

    send_confirmation(bot, user_id, lang, minutes)

    pass

def start_timer(bot, message, user_id, count, key, minutes):
    alarm_message = send_alarm_message(bot, message, user_id, count, key)
    threading.Timer(minutes * 60, alarm_message).start()


def send_alarm_message(bot, message, user_id, count, key):
    def send_alarm():

        bot_message = bot.send_message(chat_id=user_id, text=message)

        for i in range(count):
            bot.delete_message(chat_id=user_id, message_id=bot_message.message_id)
            bot_message = bot.send_message(chat_id=user_id, text=message)

        delete_backup(key)

    return send_alarm

def delete_message(bot, user_id, message_id):
    def del_msg():

        bot.delete_message(chat_id=user_id, message_id=message_id)

    return del_msg

def delete_backup(key):

    backup.delete(key)


def send_confirmation(bot, user_id, lang, minutes):
    if lang == 'EN':
        message = 'Timer for {} min. set'.format(minutes)
    else:
        message = 'Таймер на {} мин. установлен'.format(minutes)

    bot_message = bot.send_message(chat_id=user_id, text=message)
    message_id = bot_message.message_id

    del_msg = delete_message(bot, user_id, message_id)

    threading.Timer(60, del_msg).start()



def check_single_timer(user_message):

    pattern_numbers = '[0-9]+'
    pattern_words = '[^0-9\s]+'

    numbers = re.findall(pattern_numbers, user_message)
    words = re.findall(pattern_words, user_message)

    if len(numbers) == 1 and words:
        return numbers, words

    return False

def save_backup(user_id, minutes, message, count):

    current_time = datetime.now()

    key = str(user_id) + '@' + current_time.isoformat()

    backup.hmset(key, {
        'minutes': minutes,
        'message': message,
        'count': count
    })

    return key

def load_backup(bot):

    all_keys = backup.keys('*')

    for key in all_keys:

        user_id, timer_start = (key.decode()).split('@')
        timer_start = datetime.fromisoformat(timer_start)

        minutes = int(backup.hget(key, 'minutes'))
        message = backup.hget(key, 'message').decode()
        count = int(backup.hget(key, 'count'))

        timer_end = timer_start + timedelta(minutes=minutes)
        current_time = datetime.now()
        remain_time = timer_end - current_time

        if remain_time.days < 0:
            start_timer(bot, message, user_id, count, key, 0)

        else:
            start_timer(bot, message, user_id, count, key, remain_time.seconds/60)
