import logging

from state_machine.common_states import BaseSensorState

logger = logging.getLogger(__name__)

# This gives us some way of looking at long term trends
LONG_TERM_INTERVAL = 5 * 60

# Short term trends, like lid opening
SHORT_TERM_INTERVAL = 5

# Error threshold on identifying whether we are not stalling DegC/min
STALL_THRESHOLD = 0.5

# Allow a band tanslating to +/- around setpoint
SETPOINT_ERROR_PERC = 0.05

# Lid open derivative
LID_OPEN_DERIVATIVE = -10  # Celcius/min

# So below this temp we won't attempt to work if we have a flame out,
# things are too unstable below this
FLAME_OUT_DETECT_MIN_TEMP = 50

# Keeps track of the last time lid was opened
last_lid_open_timestamp = None


def is_lid_open(ctx, sensor_name):
    t_short = ctx.timestamp - SHORT_TERM_INTERVAL
    d_short = ctx.accumulators[sensor_name].linear_derivative(t_short) * 60

    return d_short < LID_OPEN_DERIVATIVE


def is_flame_out(ctx, sensor_name, temp):
    if temp < FLAME_OUT_DETECT_MIN_TEMP:
        return False
    elif last_lid_open_timestamp is not None and  (ctx.timestamp - last_lid_open_timestamp) < LONG_TERM_INTERVAL:
        # Here we are too close to the last time the lid was open, can't make a decision
        # based on historical data, as it is skewed
        return False
    else:
        t_long = ctx.timestamp - LONG_TERM_INTERVAL
        d_long = ctx.accumulators[sensor_name].linear_derivative(t_long) * 60
        return d_long < -STALL_THRESHOLD


def is_heating_again(ctx, sensor_name):
    t_short = ctx.timestamp - SHORT_TERM_INTERVAL
    d_short = ctx.accumulators[sensor_name].linear_derivative(t_short) * 60

    return d_short > STALL_THRESHOLD
 

def is_up_to_temp(temp, set_point):
    return abs(temp - set_point) <= set_point * SETPOINT_ERROR_PERC


class PitInitial(BaseSensorState):
    name = 'PIT_ANALYSING'

    def __init__(self):
        # TODO enable fan here
        pass

    """ Initial state, work out what state we're in... """

    def handle_temp(self, temp, set_point):
        if abs(temp - set_point) <= set_point * SETPOINT_ERROR_PERC:
            # Cool we are in steady state
            return UpToTemp()
        elif self.ctx.accumulators[self.sensor_name].interval() < 20:
            # Then we need to have enough data to make sense of anything
            return self
        elif temp < set_point:
            return ComingToTemp()
        else:
            return OverTemp()


class ComingToTemp(BaseSensorState):
    """ We're heating up, but keep an eye on trends ..."""
    name = 'PIT_HEATING'

    def handle_temp(self, temp, set_point):

        if is_up_to_temp(temp, set_point):
            # Cool we are in steady state
            return UpToTemp()
        elif is_lid_open(self.ctx, self.sensor_name):
            return LidOpen(self.ctx.timestamp)
        elif is_flame_out(self.ctx, self.sensor_name, temp):
            # We have a problem, we keep on trying but temp keeps going down, flame out
            return FlameOut()
        else:
            return self


class UpToTemp(BaseSensorState):
    name = 'PIT_UP_TO_TEMP'

    def handle_temp(self, temp, set_point):
        if is_up_to_temp(temp, set_point):
            # Cool we are in steady state
            return self
        elif is_lid_open(self.ctx, self.sensor_name):
            return LidOpen(self.ctx.timestamp)
        elif temp < set_point - set_point * SETPOINT_ERROR_PERC:
            return ComingToTemp()
        else:
            return OverTemp()


class OverTemp(BaseSensorState):
    name = 'PIT_OVER_TEMP'

    def handle_temp(self, temp, set_point):
        if temp < set_point + set_point * SETPOINT_ERROR_PERC:
            return UpToTemp()
        else:
            return self


class LidOpen(BaseSensorState):
    name = 'PIT_LID_OPEN'

    def __init__(self, t):
        self.begin_time = t
        global last_lid_open_timestamp
        last_lid_open_timestamp = t

    def handle_temp(self, temp, set_point):
        t_short = self.ctx.timestamp - SHORT_TERM_INTERVAL
        d_short = self.ctx.accumulators[self.sensor_name].linear_derivative(t_short) * 60

        if d_short > 1 or (self.ctx.timestamp - self.begin_time) > 2 * 60:
            # Temperature has started to climb again, or we have timed out in lid open
            return PitInitial()
        else:
            return self


class FlameOut(BaseSensorState):
    name = 'PIT_FLAME_OUT'

    def handle_temp(self, temp, set_point):
        if is_heating_again(self.ctx, self.sensor_name) or temp >= (set_point - set_point * SETPOINT_ERROR_PERC):
            # Start over again
            return PitInitial()
        else:
            return self

