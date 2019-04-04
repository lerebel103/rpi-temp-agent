import logging

from peripherals.temperature_sensors import Max31850Sensors
from notifications.notify import push_all

logger = logging.getLogger(__name__)

# How long the set point has to consistently stay above this mark for it to trigger
SETPOINT_TIME_THRESHOLD = 5

# How long we wait until the setpoint alarm is reset
ALARM_RESET_THRESHOLD = 60

# How long we wait until the setpoint alarm is reset
ALERT_SENSOR_ERROR_THRESHOLD = 60


class StateContext:
    def __init__(self, timestamp, state, temperatures, db=None):
        self.timestamp = timestamp
        self.state = state
        self.temperatures = temperatures
        self.db = db


class BBQStateMachine:
    """ Defines a generic state machine. """
    def __init__(self):
        self.current_states = {}
        self.reset()

    def reset(self):
        logger.info('Resetting state machine')
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
            return self.handle_temp(temp, set_point)
        else:
            return self.handle_error(data)

    def handle_error(self, data):
        """ Something cactus with sensor, return error state """
        # Error state transition
        if 'status' in data:
            error = data['status']
        else:
            error = Max31850Sensors.Status.UNKNOWN
        return SensorError(self.ctx.timestamp, error)

    def handle_temp(self, temp, set_point):
        pass

    def send_alarm(self, message):
        if self.ctx.db is not None:
            logger.info('Sending alarm for ' + self.sensor_name + ': ' + message)
            return push_all(self.ctx.db, 'BBQPi', message, data={})
        else:
            logger.info('Alarm not sent for ' + self.sensor_name + ', no DB.')
            return True


class SensorError(BaseSensorState):
    def __init__(self, timestamp, error):
        self.begin_time = timestamp
        self.error = error
        self._alarm_sent = False

    def handle_temp(self, temp, set_point):
        # Reset
        return SetPointInitial()

    def handle_error(self, data):
        """ So here, we are in error state, need to move out of it when things come back to normal """
        logger.debug('SensorError ' + self.sensor_name + ' ' + str(self.error))
 
        # if we are stuck in this mode over threshold, send notification
        if not self._alarm_sent and self.ctx.timestamp - self.begin_time > ALERT_SENSOR_ERROR_THRESHOLD:
            msg = 'Sensor error on {}'.format(self.sensor_name)
            self._alarm_sent = self.send_alarm(msg)

        return self


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

    def handle_temp(self, temp, set_point):
        logger.debug('SetPointOverAlarm ' + self.sensor_name)
        if not self._alarm_sent:
            msg = 'Yay,  going by {} it\'s cooked!'.format(self.sensor_name)
            self._alarm_sent = self.send_alarm(msg)
        elif temp >= set_point:
            # Keep track of last time we've been over for later
            self.begin_time = self.ctx.timestamp
        elif self.ctx.timestamp - self.begin_time > ALARM_RESET_THRESHOLD:
            # We can now reset, been under for a while now
            return SetPointUnder(self.ctx.timestamp)

        return self


