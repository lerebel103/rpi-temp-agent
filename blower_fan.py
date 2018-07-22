import logging
import threading
from time import time, sleep

import RPi.GPIO as GPIO

logger = logging.getLogger(__name__)


class BlowerFan:

    def __init__(self, gpio_pin_relay, gpio_pin_pwm, gpio_pin_rpm):
        self._pin_pwm = gpio_pin_pwm
        self._pin_relay = gpio_pin_relay
        self._pin_rpm = gpio_pin_rpm
        self._pwm_freq = 2500  # Hz
        self._pwm = None
        self._pulse_count = 0
        self._last_rpm_calc = time()
        self.is_on = False

        # A timer will continuously update rpm based on pulses received.
        self._rpm_update_thread = threading.Timer(0, self._update_rpm)
        self._reset_rpm()

    def initisalise(self):
        logger.info('Initialising Blower Fan on gpio {}'.format(self._pin_pwm))
        GPIO.setup(self._pin_relay, GPIO.OUT)

        GPIO.setup(self._pin_rpm, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(self._pin_rpm, GPIO.FALLING, self._sensed_rotation)

        GPIO.setup(self._pin_pwm, GPIO.OUT)
        self._pwm = GPIO.PWM(self._pin_pwm, self._pwm_freq)
        self._pwm.start(0)
        self._pwm.ChangeDutyCycle(0)

        logger.info('Blower Fan PWM started')

    def terminate(self):
        self.off()
        self._pwm.stop()
        logger.info('Blower Fan PWM stopped')

    def on(self):
        if not self.is_on:
            GPIO.output(self._pin_relay, 1)
            self.is_on = True
            self._rpm_update_thread.start()

    def off(self):
        if self.is_on:
            GPIO.output(self._pin_relay, 0)
            self.is_on = False
            self._rpm_update_thread.cancel()

    def rpm(self):
        return self._rpm

    def set_duty_cycle(self, duty):
        self._pwm.ChangeDutyCycle(duty)

    def _sensed_rotation(self, pin):
        self._pulse_count += 1

    def _update_rpm(self):
        self._reset_rpm()
        while self.is_on:
            now = time()
            count = self._pulse_count
            self._rpm = (count - self._last_pulse_count) / (now - self._last_rpm_calc)
            self._last_pulse_count = count
            self._rpm = self._rpm / 2  # 2 pulses per rotation
            self._last_rpm_calc = now
            sleep(1)

    def _reset_rpm(self):
        self._rpm = 0
        self._pulse_count = 0
        self._last_pulse_count = 0

