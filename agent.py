#!/usr/bin/env python
import logging
import sys
import time

import paho.mqtt.client as mqtt_client

from blower_fan import BlowerFan
from config import AgentConfig
from pacer import Pacer
from temperature_sensors import Max31850Sensors
import RPi.GPIO as GPIO

logger = logging.getLogger(__name__)


class Agent:
    def __init__(self):
        # Init GPIO
        GPIO.setmode(GPIO.BCM)

        self._config = AgentConfig()
        self._go = False
        self._temp_sensors = Max31850Sensors(self._config.temperature_gpio)
        self._blower_fan = BlowerFan(self._config.blower_fan_gpio_relay,
                                     self._config.blower_fan_gpio_pwm,
                                     self._config.blower_fan_gpio_rpm)

        # Our MQTT client
        self._client = mqtt_client.Client()

        # Setup logger
        root = logging.getLogger()
        root.setLevel(self._config.logger.level)

        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(self._config.logger.level)
        formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
        ch.setFormatter(formatter)
        root.addHandler(ch)

    def initialise(self):
        logger.info('Initialising.')

        # Initialise peripherals
        self._temp_sensors.initialise()
        self._blower_fan.initisalise()

        # Connect to MQTT
        self._client.connect_async(host=self._config.mqtt.host, port=self._config.mqtt.port)
        # Start control loop
        self._client.loop_start()

    def run(self):
        self._go = True
        self._control_loop()
        self._client.disconnect()

    def terminate(self):
        # Caues the control loop to stop
        self._go = False
        # Turn off fan as precaution
        self._blower_fan.off()
        # And comms go.
        self._client.loop_stop()

        # We are done with GPIOs.
        GPIO.cleanup()

    def _control_loop(self):
        logger.info('Running control loop.')
        pacer = Pacer()
        self._blower_fan.on()
        while self._go:
            now = time.time()

            # Tick temp sensors
            self._temp_sensors.tick(now)
            temps = ''
            for sensor in self._temp_sensors.sensors:
                temp, status = self._temp_sensors.sensor_temp(sensor)
                temps += '[{:.3f}, {}] '.format(temp, status)

            self._blower_fan.set_duty_cycle(1)
            rpm = self._blower_fan.rpm()

            # Tick all parts of the system from here
            msg = 'rpm={} temps={}, board={}'.format(rpm, temps, self._temp_sensors.board_temp())
            self._client.publish('test', msg, qos=1)

            logger.info(msg)
            # Pace control loop per desired interval
            try:
                pacer.pace(now, self._config.control_loop_seconds)
            except KeyboardInterrupt:
                self.terminate()

        self._blower_fan.off()
        logger.info('Control loop terminated.')


if __name__ == "__main__":
    agent = Agent()
    agent.initialise()
    agent.run()
