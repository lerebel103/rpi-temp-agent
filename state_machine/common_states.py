import logging

from peripherals.temperature_sensors import Max31850Sensors
from notifications.notify import push_all

logger = logging.getLogger(__name__)

# How long we wait until the setpoint alarm is reset
ALERT_SENSOR_ERROR_THRESHOLD = 60



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

    def send_alarm(self, message, data):
        if self.ctx.db is not None:
            logger.info('Sending alarm for ' + self.sensor_name + ': ' + message)
            return push_all(self.ctx.db, 'BBQPi', message, data=data)
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
        return self.ctx.probe_init_state_class()

    def handle_error(self, data):
        """ So here, we are in error state, need to move out of it when things come back to normal """
        logger.debug('SensorError ' + self.sensor_name + ' ' + str(self.error))
 
        # if we are stuck in this mode over threshold, send notification
        if not self._alarm_sent and self.ctx.timestamp - self.begin_time > ALERT_SENSOR_ERROR_THRESHOLD:
            msg = 'Sensor error on {}'.format(self.sensor_name)
            self._alarm_sent = self.send_alarm(msg,
                                               {'sensor': self.sensor_name,
                                                'error': str(self.error)})

        return self


