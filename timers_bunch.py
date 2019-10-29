import re
import threading
from collections import deque

class TimersBunch:


    def __init__(self):

        self.scheduled_bunch = deque()
        self.extended = 0
        self.additional_time = False

        self.prev_bunch = deque()
        self.current_time = 0
        self.current_timer = threading.Timer(0, None)

        pass


    def start_timer(self, next_func):

        if self.extended:
            current_time = self.extended

        elif self.scheduled_bunch:
            current_time = self.scheduled_bunch.popleft()
            self.prev_bunch.append(current_time)

        else:
            return False


        self.current_time = current_time

        self.current_timer = threading.Timer(current_time * 60, next_func)
        self.current_timer.start()


        return True


    def next_timer(self):
        self.start_timer()

    def stop_timers(self):
        self.current_timer.cancel()

    def set_current_timers_bunch(self, time_periods):
        self.scheduled_bunch = time_periods

    def get_time_periods(self, message:str):
        pattern = r'[0-9]+'
        result = [int(i) for i in re.findall(pattern, message)]

        for input in result:
            if input == 0:
                result.remove(input)

        return deque(result)

