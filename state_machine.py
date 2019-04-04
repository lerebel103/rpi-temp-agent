import logging
from datetime import datetime

from peripherals.temperature_sensors import Max31850Sensors

logger = logging.getLogger(__name__)

# How long the setpoint has to consistently stay above this mark for it to trigger
SETPOINT_TIME_THRESHOLD = 5

# How long we wait until the setpoint alarm is reset
ALARM_RESET_THRESHOLD = 60


class StateContext:
    def __init__(self, timestamp, state, temperatures):
        self.timestamp = timestamp
        self.state = state
        self.temperatures = temperatures


class BBQStateMachine:
    """ Defines a generic state machine. """
    def __init__(self):
        self.current_states = {
            'probe1': SetPointInitial(),
            'probe2': SetPointInitial(),
        }

    def run(self, ctx):
        # Run states and transition, very simple
        for sensor in self.current_states.keys():
            self.current_states[sensor] = self.current_states[sensor].run(sensor, ctx)



class BaseSensorState:
    def __init__(self):
        self.ctx = None
        self.sensor_name = None

    def run(self, sensor_name, ctx):
        self.ctx = ctx
        self.sensor_name = sensor_name
        data = ctx.temperatures.sensor_temp(sensor_name)
        if data is not None and data['status'] == Max31850Sensors.Status.OK:
            temp = data['temp']
            set_point = ctx.state[sensor_name]['setPoint']
            return self.handleTemp(temp, set_point)
        else:
            return self.handleError(data)

    def handleError(self, data):
        """ Something cactus with sensor, return error state """
        # Error state transition
        if 'status' in data:
            error = data['status']
        else:
            error = Max31850Sensors.Status.UNKNOWN
        return SensorError(error)

    def handleTemp(self, temp, set_point):
        pass


class SensorError:
    def __init__(self, error):
        self.error = error

    def run(self, sensor_name, ctx):
        """ So here, we are in error state, need to move out of it when things come back to normal """
        # TODO
        return self


class SetPointInitial(BaseSensorState):
    def handleTemp(self, temp, set_point):
        if temp < set_point:
            return SetPointUnder(self.ctx.timestamp)
        else:
            return SetPointOver(self.ctx.timestamp)


class SetPointUnder(BaseSensorState):
    def __init__(self, t):
        self.begin_time = t

    def handleTemp(self, temp, set_point):
        logger.info('SetpointUnder ' + self.sensor_name)

        # If we are above, good transition
        if temp >= set_point:
            return SetPointOver(self.ctx.timestamp)
        else:
            return self


class SetPointOver(BaseSensorState):
    def __init__(self, t):
        self.begin_time = t

    def handleTemp(self, temp, set_point):
        logger.info('SetpointOver ' + self.sensor_name)

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

    def handleTemp(self, temp, set_point):
        logger.info('SetPointOverAlarm ' + self.sensor_name)
        if not self._alarm_sent:
            self._alarm_sent = self.send_alarm()
        elif temp >= set_point:
            # Keep track of last time we've been over for later
            self.begin_time = self.ctx.timestamp
        elif self.ctx.timestamp - self.begin_time > ALARM_RESET_THRESHOLD:
            # We can now reset, been under for a while now
            return SetPointUnder(self.ctx.timestamp)

        return self

    def send_alarm(self):
        logger.info('Sending SetPointOverAlarm ' + self.sensor_name)
        return True

