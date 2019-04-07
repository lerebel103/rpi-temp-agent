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

# Lid open derivative
LID_OPEN_DERIVATIVE = -10  # Celcius/min


def is_lid_open(ctx, sensor_name):
    t_short = ctx.timestamp - SHORT_TERM_INTERVAL
    d_short = ctx.accumulators[sensor_name].linear_derivative(t_short) * 60

    return d_short < LID_OPEN_DERIVATIVE


def is_flame_out(ctx, sensor_name):
    t_long = ctx.timestamp - LONG_TERM_INTERVAL
    d_long = ctx.accumulators[sensor_name].linear_derivative(t_long) * 60

    return d_long < 0


def is_up_to_temp(temp, set_point):
    return abs(temp - set_point) <= set_point*SETPOINT_ERROR_PERC


class PitInitial(BaseSensorState):
    """ Initial state, work out what state we're in... """
    def handle_temp(self, temp, set_point):
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
    """ We're heating up, but keep an eye on trends ..."""

    def handle_temp(self, temp, set_point):

        if is_up_to_temp(temp, set_point):
            # Cool we are in steady state
            return UpToTemp()
        elif is_lid_open(self.ctx, self.sensor_name):
            return LidOpen()
        elif is_flame_out(self.ctx, self.sensor_name):
            # We have a problem, we keep on trying but temp keeps going down, flame out
            return FlameOut()
        else:
            return self


class UpToTemp(BaseSensorState):
    def handle_temp(self, temp, set_point):
        if is_up_to_temp(temp, set_point):
            # Cool we are in steady state
            return self
        elif is_lid_open(self.ctx, self.sensor_name):
            return LidOpen()
        elif is_flame_out(self.ctx, self.sensor_name):
            # We have a problem, we keep on trying but temp keeps going down, flame out
            return FlameOut()
        elif temp < set_point - set_point*SETPOINT_ERROR_PERC:
            return ComingToTemp()
        else:
            return OverTemp()


class OverTemp(BaseSensorState):
    def handle_temp(self, temp, set_point):    
        if temp < set_point + set_point*SETPOINT_ERROR_PERC:
            return UpToTemp()
        else:
            return self


class LidOpen(BaseSensorState):
    def handle_temp(self, temp, set_point):
        if is_lid_open(self.ctx, self.sensor_name):
            return self
        else:
            # Start over again
            return PitInitial()


class FlameOut(BaseSensorState):
    def handle_temp(self, temp, set_point):
        if is_flame_out(self.ctx, self.sensor_name):
            return self
        else:
            # Start over again
            return PitInitial()
