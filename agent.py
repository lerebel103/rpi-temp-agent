#!/usr/bin/env python
import json
import logging
import sys
import time

import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt_client

from controller import TempController
from pacer import Pacer
from peripherals.blower_fan import BlowerFan
from peripherals.temperature_sensors import Max31850Sensors

logger = logging.getLogger(__name__)


class Agent:
    def __init__(self):
        # Load configuration
        with open('config.json') as f:
            config = json.load(f)
        self._config = config

        # Setup logger
        root = logging.getLogger()
        level = self._config['logger']['level']
        root.setLevel(level)

        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(level)
        formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
        ch.setFormatter(formatter)
        root.addHandler(ch)

        # GPIOs
        GPIO.setmode(GPIO.BCM)

        self._go = False
        self._temp_sensors = Max31850Sensors(self._config['gpios']['temperature'],
                                             self._config['intervals']['temperature_second'])
        self._blower_fan = BlowerFan(self._config['gpios']['blower_fan_relay'],
                                     self._config['gpios']['blower_fan_pwm'],
                                     self._config['gpios']['blower_fan_rpm'])

        # Our MQTT client
        self._client = mqtt_client.Client()

        # IController
        self._controller = TempController(self._config, self._temp_sensors, self._blower_fan, self._client)

    def initialise(self):
        logger.info('Initialising.')

        # Connect to MQTT
        self._client.connect_async(host=self._config["mqtt"]["broker_host"],
                                   port=self._config["mqtt"]["broker_port"])

        # Start control loop
        self._client.on_message = self._on_mqtt_message

        # subscribe to our control topics
        self._client.subscribe(self._config['mqtt']['root_topic'] + 'controller')

        self._client.loop_start()
        # Initialise controller
        self._controller.initialise()

    def run(self):
        self._go = True
        self._control_loop()
        self._client.disconnect()

    def terminate(self):
        # Causes the control loop to stop
        self._go = False

        # Terminates communications.
        self._client.loop_stop()

        # We are done with GPIOs.
        GPIO.cleanup()

    def _control_loop(self):
        logger.info('Running control loop.')
        pacer = Pacer()
        self._controller.start()
        try:
            while self._go:
                now = time.time()
                self._controller.tick(now)

                # Pace control loop per desired interval
                try:
                    pacer.pace(now, self._config['intervals']['control_loop_second'])
                except KeyboardInterrupt:
                    self.terminate()
        finally:
            self._controller.stop()
            logger.info('Control loop terminated.')

    def _on_mqtt_message(self, client, userdata, message):
        pass


if __name__ == "__main__":
    agent = Agent()
    agent.initialise()
    agent.run()
