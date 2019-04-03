import logging
from datetime import datetime

from peripherals.temperature_sensors import Max31850Sensors

logger = logging.getLogger(__name__)

# How long the setpoint has to consistently stay above this mark for it to trigger
SETPOINT_TIME_THRESHOLD = 5

class StateContext:
    def __init__(self, state, temperatures):
        self.timestamp = None
        self.state = state
        self.temperatures = temperatures


class BBQStateMachine:
    """ Defines a generic state machine. """
    def __init__(self, ctx):
        self.current_states = {
            'probe1': SetPointInitial(),
            'probe2': SetPointInitial(),
        }
        self.ctx = ctx

    def run(self):
        # Run states and transition, very simple
        for sensor in self.current_states.keys():
            self.current_states[sensor] = self.current_states[sensor].run(sensor, self.ctx)


class SetPointInitial:
    def run(self, sensor_name, ctx):
        data = ctx.temperatures.sensor_temp(sensor_name)
        if data is not None and  data['status'] == Max31850Sensors.Status.OK:
            temp = data['temp']
            set_point = ctx.state[sensor_name]['setPoint']
            if temp < set_point:
                return SetPointUnder()
            else:
                return SetPointOver()
        return self


class SetPointUnder:
    def __init__(self):
        self.begin_time = datetime.now()

    def run(self, sensor_name, ctx):
        logger.info('SetpointUnder ' + sensor_name)

        # If we are above, good transition
        data = ctx.temperatures.sensor_temp(sensor_name)
        if data is not None and data['status'] == Max31850Sensors.Status.OK:
            temp = data['temp']
            set_point = ctx.state[sensor_name]['setPoint']
            if temp > set_point and (datetime.now() - self.begin_time).total_seconds() > SETPOINT_TIME_THRESHOLD:
                return SetPointOver()
        return self


class SetPointOver:
    def __init__(self):
        self.begin_time = datetime.now()

    def run(self, sensor_name, ctx):
        logger.info('SetpointOver ' + sensor_name)

        # If we are above, good transition
        data = ctx.temperatures.sensor_temp(sensor_name)
        if data is not None and data['status'] == Max31850Sensors.Status.OK:
            temp = data['temp']
            set_point = ctx.state[sensor_name]['setPoint']
            if temp < set_point and (datetime.now() - self.begin_time).total_seconds() > SETPOINT_TIME_THRESHOLD:
                return SetPointUnder()

        return self



