from time import sleep


class Pacer:
    def __init__(self):
        self._time_line = None

    def pace(self, time_now, interval):
        """ Paces the control loop at desired intervals. """
        if self._time_line is not None:
            sleep_time = self._time_line - time_now
            if sleep_time > 0:
                sleep(sleep_time)
        else:
            self._time_line = time_now
            sleep(interval)
        self._time_line += interval
