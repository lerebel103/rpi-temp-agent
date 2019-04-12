import logging

from state_machine.common_states import BaseSensorState
from state_machine.state_names import PIT_ANALYSING, PIT_HEATING, PIT_UP_TO_TEMP, PIT_OVER_TEMP, PIT_LID_OPEN, \
    PIT_FLAME_OUT

logger = logging.getLogger(__name__)

# This gives us some way of looking at long term trends
LONG_TERM_INTERVAL = 5 * 60  # seconds

# Short term trends, like lid opening
SHORT_TERM_INTERVAL = 5  # seconds

# Error threshold on identifying whether we are not stalling DegC/min
STALL_THRESHOLD = 0.5

# Allow a band tanslating to +/- around setpoint
SETPOINT_ERROR_PERC = 0.05

# Lid open derivative
LID_OPEN_DERIVATIVE = -10  # Celcius/min

# So below this temp we won't attempt to work if we have a flame out,
# things are too unstable below this
FLAME_OUT_DETECT_MIN_TEMP = 50

# Minimum interval (seconds) we need to go past PitInitial
ACCUMULATOR_MIN_INTERVAL = 20


def is_lid_open(ctx, sensor_name):
    """ We're just looking for a short term high negative first order derivative. """
    t_short = ctx.timestamp - SHORT_TERM_INTERVAL
    d_short = ctx.accumulators[sensor_name].linear_derivative(t_short) * 60

    return d_short < LID_OPEN_DERIVATIVE


def is_flame_out(ctx, sensor_name, temp):
    """ We're just looking for a long term first order derivative that's below threshold. """
    if temp < FLAME_OUT_DETECT_MIN_TEMP:
        return False
    else:
        t_long = ctx.timestamp - LONG_TERM_INTERVAL
        d_long = ctx.accumulators[sensor_name].linear_derivative(t_long) * 60
        return d_long < -STALL_THRESHOLD


def is_heating_again(ctx, sensor_name):
    """ We're looking for a temp rise short term (over stall threshold) """
    t_short = ctx.timestamp - SHORT_TERM_INTERVAL
    d_short = ctx.accumulators[sensor_name].linear_derivative(t_short) * 60

    return d_short > STALL_THRESHOLD


def is_up_to_temp(temp, set_point):
    return abs(temp - set_point) <= set_point * SETPOINT_ERROR_PERC


class PitInitial(BaseSensorState):
    """ Initial state, work out what state we're in... """
    name = PIT_ANALYSING

    def __init__(self):
        # As we are starting out, and could transition from any unstable state
        # we forcefully clear the accumulator to start fresh.
        #
        # A good example is when the lid has been opened for some time or we've had a flame out. In these
        # cases, the long term derivative would be negative: temp(now) - temp(long) < 0. This would trip over
        # then entire state machine, until all older temp readings are flushed with new points.
        self._reset = True

    def handle_temp(self, temp, set_point):
        if self._reset:
            self.ctx.accumulators[self.sensor_name].reset()
            self._reset = False
            return self
        elif abs(temp - set_point) <= set_point * SETPOINT_ERROR_PERC:
            # Cool we are in steady state
            return UpToTemp()
        elif self.ctx.accumulators[self.sensor_name].interval() < ACCUMULATOR_MIN_INTERVAL:
            # Then we need to have enough data to make sense of anything
            return self
        elif temp < set_point:
            return ComingToTemp()
        else:
            return OverTemp()


class ComingToTemp(BaseSensorState):
    """ We're heating up, but keep an eye on trends ..."""
    name = PIT_HEATING

    def handle_temp(self, temp, set_point):

        if is_up_to_temp(temp, set_point):
            # Cool we are in steady state
            return UpToTemp()
        elif is_lid_open(self.ctx, self.sensor_name):
            return LidOpen(self.ctx.timestamp)
        elif is_flame_out(self.ctx, self.sensor_name, temp):
            # We have a problem, we keep on trying but temp keeps going down, flame out
            return FlameOut(self.ctx.timestamp)
        else:
            return self


class UpToTemp(BaseSensorState):
    name = PIT_UP_TO_TEMP

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
    name = PIT_OVER_TEMP

    def handle_temp(self, temp, set_point):
        if temp < set_point + set_point * SETPOINT_ERROR_PERC:
            return UpToTemp()
        else:
            return self


class LidOpen(BaseSensorState):
    name = PIT_LID_OPEN

    def __init__(self, t):
        self.begin_time = t

    def handle_temp(self, temp, set_point):
        if is_heating_again(self.ctx, self.sensor_name) or (self.ctx.timestamp - self.begin_time) > 2 * 60:
            # Temperature has started to climb again, or we have timed out in lid open
            return PitInitial()
        else:
            return self


class FlameOut(BaseSensorState):
    name = PIT_FLAME_OUT

    def __init__(self, t):
        self.begin_time = t
        self.last_sent_time = t
        self._alarm_sent = False

    def handle_temp(self, temp, set_point):
        if is_heating_again(self.ctx, self.sensor_name) or temp >= (set_point - set_point * SETPOINT_ERROR_PERC):
            # Start over again
            return PitInitial()
        else:
            # Send out alarm if we are settled in this state after a short while (avoid spurious transition)
            if not self._alarm_sent and (self.ctx.timestamp - self.begin_time) > 30:
                msg = 'Flame out on {}, oh no! Help!'.format(self.sensor_name)
                self.last_sent_time = self.ctx.timestamp
                self._alarm_sent = self.send_alarm(msg,
                                                   {'sensor': self.sensor_name, 'temp': temp, 'setPoint': set_point})
            else:
                # It turns out expo does not support custom sounds, which is a problem to make this
                # work like an alarm. So instead, we repeatedly send the alert, until it is acted upon
                if self.ctx.timestamp - self.last_sent_time > 5:
                    self._alarm_sent = False

            return self
