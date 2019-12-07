"""
На входе подается бот, бд с settings

"""
import redis
import time

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

        bot.send_message(chat_id=user_id, text=message)
        backup.set(user_id, 'OK')

        time.sleep(0.05)


def get_update_notification(lang):

    if lang == 'EN':
        message = 'New feature in the bot!'

    else:
        message = 'Новая плюшка в боте!'

    return message