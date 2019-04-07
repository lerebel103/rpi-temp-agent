import logging

from state_machine.common_states import BaseSensorState

logger = logging.getLogger(__name__)


# This gives us some way of looking at long term trends
LONG_TERM_INTERVAL = 5*60

# Short term trends, like lid opening
SHORT_TERM_INTERVAL = 5

# Error threshold on identifying whether we are not stalling DegC/min
STALL_THRESHOLD = 0.1

# Allow a band tanslating to +/- around setpoint
SETPOINT_ERROR_PERC = 0.05


class PitInitial(BaseSensorState):
    """ Initial state, work out what state we're in... """
    def handle_temp(self, temp, set_point):
        print('Initial')
        if abs(temp - set_point) <= set_point*SETPOINT_ERROR_PERC:
            # Cool we are in steady state
            return UpToTemp()
        elif self.ctx.accumulators[self.sensor_name].interval() < 60:
            # Then we need to have enough data to make sense of anything
            return self
        elif temp < set_point:
            return ComingToTemp()
        else:
            return OverTemp()


class ComingToTemp(BaseSensorState):

    def handle_temp(self, temp, set_point):
        print('Coming Up to Temp')
        t_short = self.ctx.timestamp - SHORT_TERM_INTERVAL
        d_short = self.ctx.accumulators[self.sensor_name].linear_derivative(t_short)
        if d_short < -10:
            print('***** lid open')

        if abs(temp - set_point) <= set_point*SETPOINT_ERROR_PERC:
            # Cool we are in steady state
            return UpToTemp()
        elif temp < set_point:
            return self
        else:
            return OverTemp()


class UpToTemp(BaseSensorState):
    def handle_temp(self, temp, set_point):
        print('Up to Temp')
        if abs(temp - set_point) <= set_point*SETPOINT_ERROR_PERC:
            # Cool we are in steady state
            return self
        elif temp < set_point:
            return self
        return self


class OverTemp(BaseSensorState):
    def handle_temp(self, temp, set_point):    
        print('over temp')
        return self


class LidOpen(BaseSensorState):
    def handle_temp(self, temp, set_point):
        return self


class FlameOut(BaseSensorState):
    def handle_temp(self, temp, set_point):
        return self
