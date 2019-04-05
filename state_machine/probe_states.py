import logging

from peripherals.temperature_sensors import Max31850Sensors
from notifications.notify import push_all
from state_machine.common_states import BaseSensorState

logger = logging.getLogger(__name__)

# How long the set point has to consistently stay above this mark for it to trigger
SETPOINT_TIME_THRESHOLD = 5

# How long we wait until the setpoint alarm is reset
ALARM_RESET_THRESHOLD = 60

# How long we wait until the setpoint alarm is reset
ALERT_SENSOR_ERROR_THRESHOLD = 60



class SetPointInitial(BaseSensorState):
    def handle_temp(self, temp, set_point):
        if temp < set_point:
            return SetPointUnder(self.ctx.timestamp)
        else:
            return SetPointOver(self.ctx.timestamp)


class SetPointUnder(BaseSensorState):
    def __init__(self, t):
        self.begin_time = t

    def handle_temp(self, temp, set_point):
        logger.debug('SetpointUnder ' + self.sensor_name)

        # If we are above, good transition
        if temp >= set_point:
            return SetPointOver(self.ctx.timestamp)
        else:
            return self


class SetPointOver(BaseSensorState):
    def __init__(self, t):
        self.begin_time = t

    def handle_temp(self, temp, set_point):
        logger.debug('SetpointOver ' + self.sensor_name)

        # If we are above, good transition
        if temp >= set_point and self.ctx.timestamp - self.begin_time > SETPOINT_TIME_THRESHOLD:
            return SetPointOverAlarm(self.ctx.timestamp)
        elif temp >= set_point:
            return self
        else:
            return SetPointUnder(self.ctx.timestamp)


class SetPointOverAlarm(BaseSensorState):
    def __init__(self, t):
        self.begin_time = t
        self._alarm_sent = False
        self.last_sent_time = None

    def handle_temp(self, temp, set_point):
        logger.debug('SetPointOverAlarm ' + self.sensor_name)
        if not self._alarm_sent:
            msg = 'Whoohoo! {} says it\'s cooked!'.format(self.sensor_name)
            self._alarm_sent = self.send_alarm(msg,
                                               {'sensor': self.sensor_name,
                                                'set_point': set_point,
                                                'temp': temp})
            self.last_sent_time = self.ctx.timestamp
        elif temp >= set_point:
            # Keep track of last time we've been over for later
            self.begin_time = self.ctx.timestamp

            # It turns out expo does not support custom sounds, which is a problem to make this
            # work like an alarm. So instead, we repeatedly send the alert, until it is acted upon
            if self.ctx.timestamp - self.last_sent_time > 5:
                self._alarm_sent = None
        elif self.ctx.timestamp - self.begin_time > ALARM_RESET_THRESHOLD:
            # We can now reset, been under for a while now
            return SetPointUnder(self.ctx.timestamp)

        return self


