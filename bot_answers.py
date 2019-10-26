from timers_bunch import TimersBunch
from datetime import datetime

class TimeManagerBot:

    last_timer_start = 0
    extended10 = 0

    def __init__(self, user_id, lang):
        self.lang = lang
        self.user_id = user_id
        self.timers = TimersBunch()

    def get_help(self):

        if self.lang == 'EN':
            message = """To start input times you want to count. """
        else:
            message = 'Чтобы начать, введи нужное количество и значение для таймеров - например, команда 50-10-30-50 ' \
                      'создаст 4 таймера по 50, 10, 30 и 50 минут.\n'\
                      '\nРазделители между цифрами значения не имеют.'

        return message

    def check_callbak(self, message):
        """ДОполнить, что если это не таймеры"""
        time_periods = self.timers.get_time_periods(message)

        if len(time_periods) > 0:
            self.timers.set_current_timers_bunch(time_periods)
            bot_message = self.get_init_timers_message(time_periods)
            timer_on = True


        return bot_message, timer_on

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
        if self.lang == "EN":
            message = 'Timer for {} min. is started! To pause the timer, press the ⌛ button'.format(self.timers.current_time)
        else:
            message = 'Таймер на {} мин. запущен. Чтобы приостановить таймер, жми на ⌛'.format(self.timers.current_time)

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
        remain = self.timers.scheduled_bunch[0]

        if self.lang == 'EN':
            message = 'Timer for {} min. was paused. Remain {} min. Press any button to continue'.format(mins, remain)
        else:
            message = 'Таймер на {} мин. был остановлен. Осталось {} мин. Для продолжения нажми любую кнопку'.format(mins, remain)

        return message

    def get_alarm_message(self):
        if self.lang == 'EN':
            message = 'Time is over!'
        else:
            message = 'Время вышло!'
        return message

    def get_confirm_message(self):
        if self.lang == 'EN':
            message = 'You\'ve extended the current timer for {} minutes. Are you sure you don\'t want to change your' \
                      'activity?\n\nYour brain need some rest to be more productive!'.format(self.extended10*10)
        else:
            message = 'Ты продлеваешь текущий таймер уже на {} минут. Не хочешь взять перерыв?' \
                      '\n\nМозгу нужен отдых, чтобы оставаться продуктивным.'.format(self.extended10*10)
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

    def start_timer(self, next_func):
        self.last_timer_start = datetime.now()
        return self.timers.start_timer(next_func)
