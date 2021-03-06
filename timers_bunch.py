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

    def start_timer(self, next_func):
        """  Start timer. Extended time comes first, then all scheduled timers """

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
        """ In start_timer we delete first element from the queue, so here we do almost nothing """

        self.start_timer()

    def stop_timers(self):
        """ Stop current timer """

        self.current_timer.cancel()

    def set_current_timers_bunch(self, time_periods):
        """Set time periods to scheduled time"""

        self.scheduled_bunch = time_periods

    def get_time_periods(self, message:str):
        """Parse message from user and get all numbers. Discard all 0-numbers
        Possible issue - if user will input 0.5 minutes - this function will return
        just 5
        """

        pattern = r'[0-9]+'
        result = [int(i) for i in re.findall(pattern, message)]

        for input in result:
            if input == 0:
                result.remove(input)

        return deque(result)

    def clear(self):
        """Stop current timer and initiate the new one"""

        self.stop_timers()
        self.__init__()

    def repeat(self):
        """Copy all bunch of passed timers to scheduled"""

        self.scheduled_bunch = self.prev_bunch
        self.prev_bunch = deque()
        self.extended = 0
