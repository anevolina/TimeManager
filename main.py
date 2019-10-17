import time
import datetime
import threading

class Settings:
    lunch_time = datetime.time(13, 0, 0)
    dinner_time = datetime.time(19, 0, 0)
    sleep_time = datetime.time(21, 0, 0)

    min_mini = datetime.time(0, 20, 0)
    max_mini = datetime.time(0, 45, 0)

    min_midi = datetime.time(1, 20, 0)
    max_midi = datetime.time(1, 50, 0)

    min_midi_rest = datetime.time(0, 5, 0)
    max_midi_rest = datetime.time(0, 10, 0)

    def __init__(self, user_id):
        self.user_id = user_id


class User:

    # mini_period = datetime.time(0, 30, 0)
    # midi_period = datetime.time(1, 50, 0)


    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.settings = Settings(id)


    def set_settings_time(self, new_time, lunch=True):
        """use lunch = True for setting lunch_time, otherwise - dinner_time"""

        if lunch:
            self.settings.lunch_time = new_time
        else:
            self.settings.dinner_time = new_time

    def start_timers(self):
        time_before_big_break = self.time_before_break()

        minutes = time_before_big_break.seconds // 60
        mini, midi = self.calculate_periods(minutes)


    def time_before_break(self):
        current_time = datetime.datetime.now().time()

        if current_time < self.settings.lunch_time:
            duration = self.substract_time(self.settings.lunch_time, current_time)
        elif current_time < self.settings.dinner_time:
            duration = self.substract_time(self.settings.dinner_time, current_time)
        else:
            duration = self.substract_time(self.settings.sleep_time, current_time)

        return duration

    def calculate_periods(self, minutes):

        min_midi_period = self.settings.min_midi.hour * 60 + self.settings.min_midi.minute
        max_midi_period = self.settings.max_midi.hour * 60 + self.settings.max_midi.minute
        midi_count, midi_period = self.find_optimal_count(minutes, min_midi_period, max_midi_period)

        midi_rest_time = minutes - midi_count*midi_period

        midi_rest_time = self.settings.min_midi_rest.minute \
            if midi_rest_time < self.settings.min_midi_rest.minute else midi_rest_time
        midi_rest_time = self.settings.max_midi_rest.minute \
            if midi_rest_time > self.settings.max_midi_rest.minute else midi_rest_time




        print(midi_count, midi_period, midi_rest_time)


        mini = 0
        midi = midi_count
        return mini, midi

    def find_optimal_count(self, minutes, min_minutes, max_minutes):

        count = 0
        remained = max_minutes
        period_time = 0

        for i in range(min_minutes, max_minutes + 1):
            temp_minutes = minutes % i
            if temp_minutes < remained:
                remained = temp_minutes
                count = minutes // i
                period_time = i


        return count, period_time

    def substract_time(self, time_end, time_start):
        """time_end and time_start are in datetime format, and this format doesn't
        support simple subtraction, and we have to convert them first
        """

        h1 = time_end.hour
        m1 = time_end.minute
        s1 = time_end.second

        h2 = time_start.hour
        m2 = time_start.minute
        s2 = time_start.second

        t1 = datetime.timedelta(hours=h1, minutes=m1, seconds=s1)
        t2 = datetime.timedelta(hours=h2, minutes=m2, seconds=s2)

        return t1-t2


me = User(1, 'Ana')
me.start_timers()