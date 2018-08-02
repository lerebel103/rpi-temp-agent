"""PID Controller simple implementation of a Proportional-Integral-Derivative (PID)

Full Credit to https://github.com/ivmech/ivPID
"""


class PID:
    """PID Controller
    """

    def __init__(self, P=1.5, I=0.2, D=0.5):

        self.Kp = P
        self.Ki = I
        self.Kd = D

        self.sample_time = 0.00

        self._last_time = None
        self.set_point = 0.0

        self.p_term = 0.0
        self.i_term = 0.0
        self.d_term = 0.0
        self._last_error = 0.0

        # Windup Guard
        self.int_error = 0.0
        self.windup_guard = 20.0

    def update(self, current_time, measured):
        """Calculates PID value """
        error = self.set_point - measured

        if self._last_time is None:
            self._last_time = current_time

        delta_time = current_time - self._last_time
        delta_error = error - self._last_error

        self.p_term = self.Kp * error
        self.i_term += error * delta_time

        if self.i_term < -self.windup_guard:
            self.i_term = -self.windup_guard
        elif self.i_term > self.windup_guard:
            self.i_term = self.windup_guard

        self.d_term = 0.0
        if delta_time > 0:
            self.d_term = delta_error / delta_time

        # Remember last time and last error for next calculation
        self._last_time = current_time
        self._last_error = error

        output = self.p_term + (self.Ki * self.i_term) + (self.Kd * self.d_term)
        return output

    @property
    def p(self, proportional_gain):
        """Determines how aggressively the PID reacts to the current error with setting Proportional Gain"""
        self.Kp = proportional_gain

    @property
    def i(self, integral_gain):
        """Determines how aggressively the PID reacts to the current error with setting Integral Gain"""
        self.Ki = integral_gain

    @property
    def d(self, derivative_gain):
        """Determines how aggressively the PID reacts to the current error with setting Derivative Gain"""
        self.Kd = derivative_gain

    def setWindup(self, windup):
        """Integral windup, also known as integrator windup or reset windup,
        refers to the situation in a PID feedback controller where
        a large change in setpoint occurs (say a positive change)
        and the integral terms accumulates a significant error
        during the rise (windup), thus overshooting and continuing
        to increase as this accumulated error is unwound
        (offset by errors in the other direction).
        The specific problem is the excess overshooting.
        """
        self.windup_guard = windup
