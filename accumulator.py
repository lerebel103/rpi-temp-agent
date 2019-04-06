import numpy as np
import bisect


class Accumulator:

    def __init__(self, interval_max):
        self.interval_max = interval_max
        self._x = []
        self._y = []

    def add(self, timestamp, value):
        self._x.append(timestamp)
        self._y.append(value)
        self._trim()

    def length(self):
        return len(self._x)

    def interval(self):
        """ Accumulated interval up to this point. """
        if self.length() > 0:
            return self._x[-1] - self._x[0]
        else:
            return 0

    def reset(self):
        """ Flush everything to start over again. """
        self._x = []
        self._y = []

    def linear_derivative(self, from_time=None):
        """ Linear fit derivative Celcius/second, from optional desired timestamp to back of queue. """
        if self.length() < 1:
            return 0
        elif from_time is None:
            return np.polyfit(self._x, self._y, 1)[0]
        else:
            idx = bisect.bisect(self._x, from_time)
            if 0 <= idx < self.length():
                return np.polyfit(self._x[idx:], self._y[idx:], 1)[0]
            else:
                return 0

    def _trim(self):
        while self.length() > 0 and self.interval() > self.interval_max:
            self._x.pop(0)
            self._y.pop(0)


