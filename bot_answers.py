from timers_bunch import TimersBunch
from datetime import datetime
import re
import redis

from single_timer import start_single_timer, check_single_timer

class TimeManagerBot:
    """
    Define answers to user actions according to language settings,
    and reaction to callback messages
    """

    settings = redis.Redis(db=1)

    def __init__(self, user_id, lang='EN'):
        """
        :param user_id: unique identification for bot
        :param lang: define language for bot

        User settings, could be changed manually by user:
        - lang - ['EN', 'RU'] - language for the bot
        - alarm_count - INTEGER - how many times alarm message will appear
        - alarm_message - STRING - what message to show when timer's done
        - add_more - INTEGER - how many minutes will be added to extend the current timer
        - auto_start - BOOLEAN - is first timer starts automatically after user message, or it should be confirmed

        Inner variables:
        - last_timer_start - DATETIME - in what time the last timer was start
        - how_many_extended - INTEGER - how many times the last timer was extended
        - message_id - TLGR_VARIABLE - in which message id the current timer updates
        - paused - is the current timer paused
        """


        self.user_id = user_id

        self.timers = TimersBunch()

        # User settings, could be changed manually
        self.lang = lang
        self.alarm_count = 1
        self.alarm_message = ''
        self.add_more = 10
        self.auto_start = True

        # Additional variables, just for inner use
        self.last_timer_start = 0
        self.how_many_extended = 0
        self.message_id = 0
        self.paused = False

    def check_user_message(self, bot, update, settings_update):
        """Define reaction to user input - set timers or change settings"""

        message = update.message.text.strip()
        user_id = update.message.from_user.id

        timer_on = False
        bot_message = 'Something went wrong'
        prev_message = 0

        set_update = settings_update.get(user_id)

        if not set_update:
        # user doesn't want to change settings

            time_periods = self.timers.get_time_periods(message)

            if len(time_periods) > 0:
                is_single_timer = check_single_timer(message)

                if is_single_timer:
                    start_single_timer(bot, self.lang, self.alarm_count, user_id, is_single_timer)
                    bot_message = ''

                else:

                    prev_message = self.message_id

                    self.refresh_timers()
                    self.timers.set_current_timers_bunch(time_periods)
                    bot_message = self.get_init_timers_message(time_periods)
                    timer_on = True
        else:
            bot_message = self.set_settings(user_id, message, settings_update, set_update)

        return bot_message, timer_on, prev_message

    def set_settings(self, user_id, message, settings_update, set_update):
        """Check what kind of settings a user wants to change,
        verify their input and save new parameter in database"""

        bot_message = 'Something went wrong in settings'

        if set_update == 'alarm_message':
            self.alarm_message = message
            bot_message = self.get_setted_alarm_message_message()
            settings_update.pop(user_id)

        elif set_update == 'alarm_count':
            count = self.check_is_number(message)
            if count:
                self.alarm_count = int(message)
                bot_message = self.get_setted_alarm_count_message()
                settings_update.pop(user_id)
            else:
                bot_message = self.get_wrong_format_message('alarm_count')

        elif set_update == 'add_more':
            count = self.check_is_number(message)

            if count:
                self.add_more = int(message)
                bot_message = self.get_setted_add_more_message()
                settings_update.pop(user_id)
            else:
                bot_message = self.get_wrong_format_message('add_more')

        self.save_settings(set_update)

        return bot_message

    def start_timer(self, next_func):
        """Start new thread with timer"""

        self.last_timer_start = datetime.now()
        return self.timers.start_timer(next_func)

    def refresh_timers(self):
        """Set all timers settings to 0"""

        self.timers.clear()

        self.last_timer_start = 0
        self.how_many_extended = 0
        self.message_id = 0

    # generate messages for bot answers

    def get_help_message(self):
        if self.lang == 'EN':
            message = 'To start, input times in minutes you want to count. For example, command 50-10-50-30 will create ' \
                      '4 timers with 50, 10, 50 and 30 minutes. Delimiters between numbers don\'t matter.' \
                      '\n\n/settings  command will return the current settings for timers.' \
                      '\n\n ---------- ' \
                      '\n\n❗ New feature! Simple timer-reminder - all I need is a number of minutes and a message! ' \
                      'Give me a message like - *"10 Call mom"* -, and after 10 minutes ' \
                      'I\'ll send you the message - *"Call mom"*.'
        else:
            message = 'Чтобы начать, введи нужное количество и значение для таймеров в минутах. Например, команда 50-10-30-50 ' \
                      'создаст 4 таймера по 50, 10, 30 и 50 минут.\n'\
                      '\nРазделители между цифрами значения не имеют.' \
                      '\n\nкоманда  /settings  выведет текущие настройки таймеров.' \
                      '\n\n ----------'\
                      '\n\n❗ Новая плюшка - таймер-напоминалка - одиночный таймер без остановки, ' \
                      'продления, повторения и т.д. - просто введи количество минут, и сообщение, которое нужно прислать.' \
                      '\n\nНапример, сообщение *"10 Позвонить маме"*  запустит таймер на 10 минут, и по окончанию выдаст сообщение ' \
                      '- *"Позвонить маме"*'


        return message

    def get_current_timer_message(self):
        if self.timers.scheduled_bunch:
            next_timer = self.timers.scheduled_bunch[0]
        else:
            return False

        if self.lang == "EN":
            message = 'The current timer is for ' + str(next_timer) + ' minutes. Press start!'
        else:
            message = 'Запускаем таймер на ' + str(next_timer) + ' минут? Жми старт!'

        return message

    def get_init_timers_message(self, time_periods):

        if len(time_periods) == 1:
            if self.lang == 'EN':
                message = 'There will be 1 timer set for ' + str(time_periods[0]) + ' minutes'
            else:
                message = 'Будет установлен 1 таймер на ' + str(time_periods[0]) + ' минут'

        else:
            timers = self.get_timers_count(time_periods)

            if self.lang == 'EN':

                message = 'There will be {} timers set for '.format(len(time_periods)) + timers + ' minutes'
            else:
                message = 'Будут установлены таймеры ({}шт) на '.format(len(time_periods)) + timers + ' минут'

        return message

    def get_started_timer_message(self):
        timer_number = len(self.timers.prev_bunch)

        if self.timers.additional_time:
            if self.lang == "EN":
                message = 'Timer #{} extended for {} min. To pause the timer, press the ⌛ button'\
                    .format(timer_number, self.timers.current_time)
            else:
                message = 'Таймер #{} продлен на {} мин. Чтобы приостановить, жми на ⌛' \
                    .format(timer_number, self.timers.current_time)

        elif self.timers.extended:
            self.timers.extended = 0

            if self.lang == "EN":
                message = 'Timer #{} resumed for the rest of {} min. To pause the timer, press the ⌛ button' \
                    .format(timer_number, self.timers.current_time)
            else:
                message = 'Таймер #{} возобновлен на оставшиеся {} мин. Чтобы приостановить, жми на ⌛' \
                    .format(timer_number, self.timers.current_time)

        else:

            if self.lang == "EN":
                message = 'Timer #{} for {} min. started! To pause the timer, press the ⌛ button'\
                    .format(timer_number, self.timers.current_time)
            else:
                message = 'Таймер #{} на {} мин. запущен. Чтобы приостановить таймер, жми на ⌛'\
                    .format(timer_number, self.timers.current_time)

        return message

    def get_finished_timer_message(self):
        timer_number = len(self.timers.prev_bunch)

        if self.lang == 'EN':
            if self.timers.scheduled_bunch:
                message = message = 'Timer #{} for {} min. just finished. Continue?'.format(timer_number, self.timers.current_time)
            else:
                message = 'All timers have finished! Well done!'
        else:
            if self.timers.scheduled_bunch:
                message = message = 'Таймер #{} на {} мин. завершен. Продолжаем?'.format(timer_number, self.timers.current_time)
            else:
                message = 'Все таймеры завершены! Время отдыхать 💃'

        return message

    def get_paused_timer_message(self):
        mins = self.timers.current_time
        remain = self.timers.extended

        if self.lang == 'EN':
            message = 'Timer for {} min. was paused. Remain {} min. Press start to continue'.format(mins, remain)
        else:
            message = 'Таймер на {} мин. был остановлен. Осталось {} мин. Для продолжения жми старт'.format(mins, remain)

        return message

    def get_alarm_message(self):

        if self.alarm_message:
            message = self.alarm_message

        elif self.lang == 'EN':
            message = 'Time is over!'
        else:
            message = 'Время вышло!'
        return message

    def get_confirm_message(self):
        if self.lang == 'EN':
            message = 'You\'ve extended the current timer for {} minutes. Are you sure you don\'t want to change your' \
                      'activity?\n\nYour brain needs some rest to be more productive!'.format(self.how_many_extended * self.add_more)
        else:
            message = 'Ты продлеваешь текущий таймер уже на {} минут. Не хочешь взять перерыв?' \
                      '\n\nМозгу нужен отдых, чтобы оставаться продуктивным.'.format(self.how_many_extended * self.add_more)
        return message

    def get_settings_message(self):
        if self.lang == 'EN':
            message = 'Settings: ' \
                      '\n\n/language - сменить язык. Текущий - {}' \
                      '\n\n/alarm_count - to change how many times an alarm message will appear. The current - {}' \
                      '\n\n/alarm_message - to change the current alarm message. The current - "{}"' \
                      '\n\n/add_more - to change default value for adding more minutes to timer. The current - {} min' \
                      '\n\n/auto_start - to start first timer automatically. The current - {}'\
                .format(self.lang, self.alarm_count, self.get_alarm_message(), self.add_more, self.auto_start)
        else:
            message = 'Настройки: ' \
                      '\n\n/language - to change language. The current - {}' \
                      '\n\n/alarm_count - задать, сколько раз будет приходить оповещение об окончании таймера. Сейчас - {}' \
                      '\n\n/alarm_message - задать текст оповещения. Сейчас - "{}"' \
                      '\n\n/add_more - задать, сколько минут будет добавляться к таймеру для продления. Сейчас - {} min' \
                      '\n\n/auto_start - стартовать первый таймер из серии автоматически. Текущее значение - {}' \
                .format(self.lang, self.alarm_count, self.get_alarm_message(), self.add_more, self.auto_start)

        return message

    def get_updated_language_message(self):
        if self.lang == 'EN':
            message = 'Language changed'
        else:
            message = 'Язык изменен'
        return message

    def get_set_alarm_count_message(self):
        if self.lang == 'EN':
            message = 'The current parameter will set how many times an alarm message will appear. The current value - {}' \
                      '\n\nTo cancel changes input /cancel command'.format(self.alarm_count)
        else:
            message = 'Данный параметр устанавливает, сколько раз будет приходить оповещение об окончании таймера.' \
                      'Текущее значение - {}.\n\nДля отмены изменений введи команду /cancel'.format(self.alarm_count)
        return message

    def get_setted_alarm_count_message(self):
        if self.lang == 'EN':
            message = '/alarm_count parameter was changed. The current value - {}'.format(self.alarm_count)
        else:
            message = '/alarm_count параметр был изменен. Текущее значение - {}'.format(self.alarm_count)
        return message

    def get_set_alarm_message_message(self):
        if self.lang == 'EN':
            message = 'The current parameter will define a message for alarm after a timer will have finished.' \
                      'The current value - {}.\n\nTo cancel changes input /cancel command'.format(self.get_alarm_message())
        else:
            message = 'Данный параметр задает текст сообщения об окончании таймера. Текущее значение - {}' \
                      '\n\nДля отмены изменений введи команду /cancel'.format(self.get_alarm_message())
        return message

    def get_setted_alarm_message_message(self):
        if self.lang == 'EN':
            message = '/alarm_message parameter was changed. The current value - {}'.format(self.alarm_message)
        else:
            message = '/alarm_message параметр был изменен. Текущее значение - {}'.format(self.alarm_message)
        return message

    def get_set_add_more_message(self):
        if self.lang == 'EN':
            message = 'The current parameter will define how many minutes will be automatically added with \'🕝  Gimme more\' ' \
                      'button. The current value - {}.\n\nTo cancel changes input /cancel command'.format(self.add_more)

        else:
            message = 'Данный параметр задает, сколько минут будет добавлено при нажатии на кнопку \'🕝  Добавь еще!\'' \
                      'Текущее значение - {}.\n\nДля отмены изменений введи команду /cancel'.format(self.add_more)
        return message

    def get_setted_add_more_message(self):
        if self.lang == 'EN':
            message = '/add_more parameter was changed. The current value - {}'.format(self.add_more)
        else:
            message = '/add_more параметр был изменен. Текущее значение - {}'.format(self.add_more)
        return message

    def get_set_auto_start_message(self):

        if self.lang == 'EN':
            if self.auto_start:
                message = 'The first timer starts automatically'
            else:
                message = 'All timers have to be started manually'
        else:
            if self.auto_start:
                message = 'Первый таймер запускается автоматически'
            else:
                message = 'Все таймеры запускаются вручную'

        return message

    def get_cancel_message(self):
        if self.lang == 'EN':
            message = 'Сhanges canceled'
        else:
            message = 'Изменения отменены'
        return message

    def get_wrong_format_message(self, set_parameter):
        if self.lang == 'EN':
            message = 'Wrong format message to set /{} parameter. Waiting for a single number.' \
                      '\n\nTo cancel changes input /cancel command'.format(set_parameter)
        else:
            message = 'Неправильный формат сообщения для установки параметра /{}. Ожидается одно число.' \
                      '\n\nДля отмены изменений введи команду /cancel'.format(set_parameter)
        return message

    def get_remained_message(self, minutes):
        if self.lang == 'EN':
            message = 'Remain {} min'.format(minutes)
        else:
            message = 'Осталось {} мин.'.format(minutes)

        return message

    def get_old_timers_message(self):

        if self.lang == 'EN':
            message = 'The new bunch of timers was set. Previous timers are no longer exist.'
        else:
            message = 'Установлены новые таймеры. Предыдущие таймеры больше не существуют'

        return message

    def get_timers_count(self, time_periods):

        if len(time_periods) == 1:
            return str(time_periods[0])

        else:
            timers = ', '.join([str(time_periods[i]) for i in range(len(time_periods)-1)])

            if self.lang == 'EN':
                timers += ' and ' + str(time_periods[-1])
            else:
                timers += ' и ' + str(time_periods[-1])

        return timers

    def save_settings(self, set_update):
        """Save settings to redis db"""

        if set_update == 'lang' or set_update == 'ALL':
            self.settings.hset(self.user_id, 'lang', self.lang)

        if set_update == 'alarm_count' or set_update == 'ALL':
            self.settings.hset(self.user_id, 'alarm_count', self.alarm_count)

        if set_update == 'alarm_message' or set_update == 'ALL':
            self.settings.hset(self.user_id, 'alarm_message', self.alarm_message)

        if set_update == 'add_more' or set_update == 'ALL':
            self.settings.hset(self.user_id, 'add_more', self.add_more)

        if set_update == 'auto_start' or set_update == 'ALL':
            self.settings.hset(self.user_id, 'auto_start', int(self.auto_start))

        return

    def load_settings(self):
        """Load settings for an user"""

        self.lang = self.settings.hget(self.user_id, 'lang').decode()
        self.alarm_count = int(self.settings.hget(self.user_id, 'alarm_count'))
        self.alarm_message = self.settings.hget(self.user_id, 'alarm_message').decode()
        self.add_more = int(self.settings.hget(self.user_id, 'add_more'))
        self.auto_start = bool(self.settings.hget(self.user_id, 'auto_start'))


    # Additional functions

    def check_is_number(self, message):
        """Check if the message is just a number"""

        is_single_number = re.fullmatch(r'[0-9]+', message.strip())

        return is_single_number

