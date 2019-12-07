"""
На входе подается бот, бд с settings

"""
import redis
import time
from telegram import ParseMode


backup = redis.Redis(db=4)

def send_update_notification(bot, db_number):

    db = redis.Redis(db=db_number)

    notified_users = list(map(int, backup.keys('*')))

    all_users = db.keys('*')

    for user in all_users:

        user_id = int(user)

        if user_id in notified_users:
            continue

        lang = db.hget(user_id, 'lang').decode()

        message = get_update_notification(lang)

        bot.send_message(chat_id=user_id, text=message, parse_mode=ParseMode.MARKDOWN)
        backup.set(user_id, 'OK')

        time.sleep(0.05)


def get_update_notification(lang):

    if lang == 'EN':
        message = '❗ New feature in the bot! Simple timer-reminder - all I need is a number of minutes and a message! ' \
                    '\n\nGive me a message like *"10 Call mom"*, and after 10 minutes ' \
                    'I\'ll send you the message - *"Call mom"*.'

    else:
        message = '❗ Новая плюшка в боте - таймер-напоминалка - одиночный таймер без остановки, ' \
                      'продления, повторения и т.д. - просто введи количество минут, и сообщение, которое нужно прислать.' \
                      '\n\nНапример, сообщение *"10 Позвонить маме"*  запустит таймер на 10 минут, и по окончанию выдаст сообщение ' \
                      '- *"Позвонить маме"*'

    return message