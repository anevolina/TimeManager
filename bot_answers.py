from timers_bunch import TimersBunch
from datetime import datetime
import re

class TimeManagerBot:

    def __init__(self, user_id, lang):

        self.user_id = user_id

        self.timers = TimersBunch()

        self.lang = lang
        self.alarm_count = 1
        self.alarm_message = ''
        self.add_more = 10
        self.auto_start = True

        self.last_timer_start = 0
        self.extended10 = 0
        self.message_id = 0

    def check_callbak(self, message, settings_update, user_id):

        timer_on = False
        bot_message = 'Something went wrong'
        prev_message = 0

        set_update = settings_update.get(user_id)

        if not set_update:

            time_periods = self.timers.get_time_periods(message)

            if len(time_periods) > 0:

                prev_message = self.message_id

                self.refresh_timers()
                self.timers.set_current_timers_bunch(time_periods)
                bot_message = self.get_init_timers_message(time_periods)
                timer_on = True
        else:
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

        return bot_message, timer_on, prev_message

    def start_timer(self, next_func):
        self.last_timer_start = datetime.now()
        return self.timers.start_timer(next_func)

    def refresh_timers(self):

        self.timers.clear()

        self.last_timer_start = 0
        self.extended10 = 0
        self.message_id = 0


    # generate messages for bot answers

    def get_help_message(self):

        if self.lang == 'EN':
            message = 'To start input times in minutes you want to count. For example, command 50-10-50-30 will create' \
                      '4 timers with 50, 10, 50 and 30 minutes. Delimiters between numbers don\'t matter.' \
                      '\n\n/settings  command will return current settings for timers.'
        else:
            message = 'Чтобы начать, введи нужное количество и значение для таймеров в минутах - например, команда 50-10-30-50 ' \
                      'создаст 4 таймера по 50, 10, 30 и 50 минут.\n'\
                      '\nРазделители между цифрами значения не имеют.' \
                      '\n\nкоманда  /settings  выведет текущие настройки таймеров.'

        return message

    def get_current_timer_message(self):
        if self.timers.scheduled_bunch:
            next_timer = self.timers.scheduled_bunch[0]
        else:
            return False

        if self.lang == "EN":
            message = 'Current timer is for ' + str(next_timer) + ' minutes. Press start!'
        else:
            message = 'Запускаем таймер на ' + str(next_timer) + ' минут? Жми старт!'

        return message

    def get_init_timers_message(self, time_periods):

        if len(time_periods) == 1:
            if self.lang == 'EN':
                message = 'There will be set 1 timer for ' + str(time_periods[0]) + ' minutes'
            else:
                message = 'Будет установлен 1 таймер на ' + str(time_periods[0]) + ' минут'

        else:
            timers = self.get_timers_count(time_periods)

            if self.lang == 'EN':

                message = 'There will be set {} timers for '.format(len(time_periods)) + timers + ' minutes'
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
            if self.lang == "EN":
                message = 'Timer #{} was resumed for the rest {} min. To pause the timer, press the ⌛ button' \
                    .format(timer_number, self.timers.current_time)
            else:
                message = 'Таймер #{} возобновлен на оставшиеся {} мин. Чтобы приостановить, жми на ⌛' \
                    .format(timer_number, self.timers.current_time)

        else:

            if self.lang == "EN":
                message = 'Timer #{} for {} min. is started! To pause the timer, press the ⌛ button'\
                    .format(timer_number, self.timers.current_time)
            else:
                message = 'Таймер #{} на {} мин. запущен. Чтобы приостановить таймер, жми на ⌛'\
                    .format(timer_number, self.timers.current_time)

        return message

    def get_finished_timer_message(self):
        if self.lang == 'EN':
            if self.timers.scheduled_bunch:
                message = message = 'Timer for {} min. just finished. Continue?'.format(self.timers.current_time)
            else:
                message = 'All timers have finished! Well done!'
        else:
            if self.timers.scheduled_bunch:
                message = message = 'Таймер на {} мин. завершен. Продолжаем?'.format(self.timers.current_time)
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
                      'activity?\n\nYour brain need some rest to be more productive!'.format(self.extended10*self.add_more)
        else:
            message = 'Ты продлеваешь текущий таймер уже на {} минут. Не хочешь взять перерыв?' \
                      '\n\nМозгу нужен отдых, чтобы оставаться продуктивным.'.format(self.extended10*self.add_more)
        return message

    def get_settings_message(self):
        if self.lang == 'EN':
            message = 'Settings: ' \
                      '\n\n/language - сменить язык. Текущий - {}' \
                      '\n\n/alarm_count - to change how many times alarm message will appear. Current - {}' \
                      '\n\n/alarm_message - to change current alarm message. Current - "{}"' \
                      '\n\n/add_more - to change default value for adding more minutes to timer. Current - {} min' \
                      '\n\n/auto_start - to start first timer automatically. Current - {}'\
                .format(self.lang, self.alarm_count, self.get_alarm_message(), self.add_more, self.auto_start)
        else:
            message = 'Настройки: ' \
                      '\n\n/language - to change language. Current - {}' \
                      '\n\n/alarm_count - задать, сколько раз будет приходить оповещение об окончании таймера. Сейчас - {}' \
                      '\n\n/alarm_message - задать текст оповещения. Сейчас - "{}"' \
                      '\n\n/add_more - задать, сколько минут будет добавляться к таймеру для продления. Сейчас - {} min' \
                      '\n\n/auto_start - стартовать первый таймер из серии автоматически. Текущее значение - {}' \
                .format(self.lang, self.alarm_count, self.get_alarm_message(), self.add_more, self.auto_start)

        return message

    def get_updated_language_message(self):
        if self.lang == 'EN':
            message = 'Language has been changed'
        else:
            message = 'Язык изменен'
        return message

    def get_set_alarm_count_message(self):
        if self.lang == 'EN':
            message = 'Current parameter will set how many times alarm message will appeare. Current value - {}' \
                      '\n\nTo cancel changes input /cancel command'.format(self.alarm_count)
        else:
            message = 'Данный параметр устанавливает, сколько раз будет приходить оповещение об окончании таймера.' \
                      'Текущее значение - {}.\n\nДля отмены изменений введи команду /cancel'.format(self.alarm_count)
        return message

    def get_setted_alarm_count_message(self):
        if self.lang == 'EN':
            message = '/alarm_count parameter was changed. Current value - {}'.format(self.alarm_count)
        else:
            message = '/alarm_count параметр был изменен. Текущее значение - {}'.format(self.alarm_count)
        return message

    def get_set_alarm_message_message(self):
        if self.lang == 'EN':
            message = 'Current parameter will define a message for alarm after a timer will have finished.' \
                      'Current value - {}.\n\nTo cancel changes input /cancel command'.format(self.alarm_message)
        else:
            message = 'Данный параметр задает текст сообщения об окончании таймера. Текущее значение - {}' \
                      '\n\nДля отмены изменений введи команду /cancel'.format(self.alarm_message)
        return message

    def get_setted_alarm_message_message(self):
        if self.lang == 'EN':
            message = '/alarm_message parameter was changed. Current value - {}'.format(self.alarm_message)
        else:
            message = '/alarm_message параметр был изменен. Текущее значение - {}'.format(self.alarm_message)
        return message

    def get_set_add_more_message(self):
        if self.lang == 'EN':
            message = 'Current parameter will define how many minutes will be automaticly added with \'Give me more minutes  🤓\' ' \
                      'button. Current value - {}.\n\nTo cancel changes input /cancel command'.format(self.add_more)

        else:
            message = 'Данный параметр задает, сколько минут будет добавлено при нажатии на кнопку \'Мне нужно еще время!  🤓\'' \
                      'Текущее значение - {}.\n\nДля отмены изменений введи команду /cancel'.format(self.add_more)
        return message

    def get_setted_add_more_message(self):
        if self.lang == 'EN':
            message = '/add_more parameter was changed. Current value - {}'.format(self.add_more)
        else:
            message = '/add_more параметр был изменен. Текущее значение - {}'.format(self.add_more)
        return message

    def get_set_auto_start_message(self):

        if self.lang == 'EN':
            if self.auto_start:
                message = 'First timer starts automatically'
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
            message = 'Сhanges have been canceled'
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
            message = '{} min. remain'.format(minutes)
        else:
            message = '{} мин. осталось'.format(minutes)

        return message

    def get_old_timers_message(self):

        if self.lang == 'EN':
            message = 'New bunch of timers were wet. Current timers are no longer exist.'
        else:
            message = 'Установлены новые таймеры. Текущие таймеры больше не существуют'

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

    # Additional functions

    def check_is_number(self, message):
        is_single_number = re.fullmatch(r'[0-9]+', message.strip())

        return is_single_number

