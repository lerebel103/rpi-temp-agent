#!/usr/bin/env python
import logging
import sys
import time

import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt_client

from config import AgentConfig
from pacer import Pacer
from peripherals.blower_fan import BlowerFan
from peripherals.temperature_sensors import Max31850Sensors
from pid import PID

logger = logging.getLogger(__name__)


class Agent:
    def __init__(self):
        # Init GPIO
        GPIO.setmode(GPIO.BCM)

        self._config = AgentConfig()
        self._go = False
        self._temp_sensors = Max31850Sensors(self._config.temperature_gpio, self._config.temperature_sample_interval)
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
        # Causes the control loop to stop
        self._go = False

        # Turn off fan as precaution
        if self._blower_fan.is_on:
            self._blower_fan.off()

        # Terminates communications.
        self._client.loop_stop()

        # We are done with GPIOs.
        GPIO.cleanup()

    def _control_loop(self):
        logger.info('Running control loop.')
        pacer = Pacer()
        self._blower_fan.on()
        self._temp_sensors.on()

        # Here's our PID
        pid = PID()
        pid.set_point = 40

        try:
            while self._go:
                now = time.time()

                # Read sensor temps
                bbq_temp = None
                temps = ''
                for sensor in self._temp_sensors.sensors:
                    temp, status = self._temp_sensors.sensor_temp(sensor)
                    if temp is not None and status == Max31850Sensors.Status.OK:
                        bbq_temp = temp
                        temps += '[{:.3f}, {}] '.format(temp, status)
                    else:
                        bbq_temp = None
                        temps += '[--, {}] '.format(status)

                if bbq_temp is not None:
                    output = pid.update(now, bbq_temp)
                    # Set fan duty cycle
                    print(output)
                    self._blower_fan.duty_cycle = output

                rpm = self._blower_fan.rpm

                if not self._blower_fan.is_healthy:
                    print("**************** FAN NOT SPINNING.")

                # Tick all parts of the system from here
                msg = 'rpm={} temps={}, board={}'.format(rpm, temps, self._temp_sensors.board_temp())
                self._client.publish('test', msg, qos=1)

                logger.info(msg)
                # Pace control loop per desired interval
                try:
                    pacer.pace(now, self._config.control_loop_seconds)
                except KeyboardInterrupt:
                    self.terminate()
        finally:
            self._temp_sensors.off()
            self._blower_fan.off()
            logger.info('Control loop terminated.')


if __name__ == "__main__":
    agent = Agent()
    agent.initialise()
    agent.run()
