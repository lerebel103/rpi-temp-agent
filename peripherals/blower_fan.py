import logging
import threading
from time import time, sleep

import RPi.GPIO as GPIO

logger = logging.getLogger(__name__)


class BlowerFan:
    """ Controls the Blower fan by using PWM. """

    def __init__(self, gpio_pin_relay, gpio_pin_pwm, gpio_pin_rpm):
        self._pin_pwm = gpio_pin_pwm
        self._pin_relay = gpio_pin_relay
        self._pwm_freq = 1600  # Hz
        self._pwm = None
        self._duty_cycle = 0
        self.is_on = False
        self._pulse_counter = RpmPulseCounter(gpio_pin_rpm)

    def initisalise(self):
        logger.info('Initialising Blower Fan on gpio {}'.format(self._pin_pwm))

        # PWM pin
        GPIO.setup(self._pin_pwm, GPIO.OUT)
        self._pwm = GPIO.PWM(self._pin_pwm, self._pwm_freq)

        # ON/OFF Relay
        GPIO.setup(self._pin_relay, GPIO.OUT)

        # RPM handler
        self._pulse_counter.initialise()

        logger.info('Blower Fan initialised.')

    def on(self):
        """ Switches the fan on, start PWM and start monitoring RPM. """
        if not self.is_on:
            # Start RPM pulse counter
            self._pulse_counter.start()
            # Start PWM
            self._pwm.start(self.duty_cycle)
            # Switch fan on
            GPIO.output(self._pin_relay, 1)
            self.is_on = True
            logger.info('Blower Fan started.')

    def off(self):
        """ Switches the fan off, stops PWM and stops monitoring RPM. """
        if self.is_on:
            # Switch fan off
            GPIO.output(self._pin_relay, 0)
            # Switch PWM off
            self.duty_cycle = 0
            self._pwm.stop()
            # Switch pulse counter off
            self._pulse_counter.stop()
            self.is_on = False
            logger.info('Blower Fan PWM stopped.')

    @property
    def rpm(self):
        """ Read RPM from Sensor wire. """
        return self._pulse_counter.rpm

    @property
    def duty_cycle(self):
        """ Current duty cycle at which the Fan is running. """
        return self._duty_cycle

    @duty_cycle.setter
    def duty_cycle(self, duty_cycle):
        """ Specifies PWM duty cycle to run the fan at.
        \:param duty [0-100]
        """
        self._pwm.ChangeDutyCycle(duty_cycle)
        self._duty_cycle = duty_cycle

    @property
    def is_healthy(self):
        """ Checks that fan is spinning when we expect it to. """
        if self.is_on and self.duty_cycle > 0 and self.rpm == 0:
            return False
        else:
            return True

class RpmPulseCounter:
    """ Simple wrapper that counts pulses from the Fan's yellow wire to deduce RPM. """

    def __init__(self, gpio_pin_rpm):
        """ Creates this instance by binding it to a pin.

        \:param gpio_pin_rpm: Input pin to which the fan Sensor wire is connected.
        """
        self._pin_rpm = gpio_pin_rpm
        self.is_on = False
        self._rpm_update_thread = None
        self._reset_rpm()

    def initialise(self):
        logger.info('Initialising Blower Fan RPM Sensor on gpio {}'.format(self._pin_rpm))
        # Safety so we can re-init and go again potentially
        self.stop()

        # Set up our pins as input, with event call back
        GPIO.setup(self._pin_rpm, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(self._pin_rpm, GPIO.FALLING, self._sensed_rotation)

        # A timer will continuously update rpm based on pulses received.
        self._rpm_update_thread = threading.Timer(0, self._update_rpm_loop)
        self._rpm_update_thread.daemon = True
        logger.info('Initialised RPM pulse counter on gpio {}'.format(self._pin_rpm))

    def start(self):
        """ Start counting pulses in a background thread. """
        if not self.is_on:
            self.is_on = True
            self._rpm_update_thread.start()
            logger.info('Started RPM pulse counter on gpio {}'.format(self._pin_rpm))

    def stop(self):
        """ Start counting pulses in a background thread. """
        if self.is_on:
            self._rpm_update_thread.cancel()
            self.is_on = False
            logger.info('Stopped RPM pulse counter on gpio {}'.format(self._pin_rpm))

    @property
    def rpm(self):
        """ RPM value as computed from pulses. """
        return self._rpm

    def _reset_rpm(self):
        self._rpm = 0
        self._pulse_count = 0
        self._last_pulse_count = 0
        self._last_pulse_time = time()
        self._last_rpm_calc = time()

    def _sensed_rotation(self, pin):
        """ Called back with pin for which the event occured. """
        now = time()
        # Filter out spurious pulses (good for 5,000 RPM with this check)
        if now - self._last_pulse_time > 0.001:
            self._pulse_count += 1
        self._last_pulse_time = now

    def _update_rpm_loop(self):
        """ Continuously runs at regular intervals to update the effective RPM value."""
        self._reset_rpm()
        while self.is_on:
            now = time()
            count = self._pulse_count
            self._rpm = (count - self._last_pulse_count) / (now - self._last_rpm_calc)
            self._rpm = 60 * self._rpm / 2  # 2 pulses per rotation

            self._last_rpm_calc = now
            self._last_pulse_count = count
            sleep(1)  # 1 second resolution, plenty good.
