import re
import threading
from collections import deque

class TimersBunch:
    scheduled_bunch = deque()
    prev_bunch = deque()
    current_time = 0
    current_timer = threading.Timer(0, None)

    def __init__(self):

        # time_periods = self.get_time_periods(message)
        # self.set_current_timers_bunch(time_periods)
        pass


    def start_timer(self, next_func):

        if self.scheduled_bunch:
            current_timer = self.scheduled_bunch.popleft()
            self.prev_bunch.append(current_timer)
            self.current_time = current_timer
            self.current_timer = threading.Timer(current_timer, next_func)
            self.current_timer.start()
            return True
        else:
            return False

    def next_timer(self):
        self.start_timer()

    def stop_timers(self):
        self.current_timer.cancel()

    def set_current_timers_bunch(self, time_periods: list):
        self.scheduled_bunch = time_periods

    def get_time_periods(self, message:str):
        pattern = r'[0-9]+'
        result = [int(i) for i in re.findall(pattern, message)]

        for input in result:
            if input == 0:
                result.remove(input)

        return deque(result)

