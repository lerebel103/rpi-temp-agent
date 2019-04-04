#!/usr/bin/env python
import json
import logging
import sys
import time
import argparse

import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt_client

from controller import TempController
from hardware_id import get_cpu_id
from pacer import Pacer
from peripherals.blower_fan import BlowerFan
from peripherals.temperature_sensors import Max31850Sensors
from commands import Commands

from db.data_logger import DataLogger

logger = logging.getLogger(__name__)


class Agent:
    def __init__(self):
        # Load configuration
        with open('config/config.json') as f:
            config = json.load(f)
        self._config = config

        # Do logger
        self._setup_logger()
        logger.info('HardwareID={}'.format(get_cpu_id()))

        # GPIOs
        GPIO.setmode(GPIO.BCM)

        self._go = False
        self._temp_sensors = Max31850Sensors(self._config['temperature'])
        self._blower_fan = BlowerFan(self._config['fan'])

        # Our MQTT client
        self._client = mqtt_client.Client(client_id=get_cpu_id())

        # Data logger
        self._data_logger = DataLogger(config['data_logger']['path'], get_cpu_id())

        # IController
        self._controller = TempController(self._config, self._temp_sensors, self._blower_fan, self._client,
                                          self._data_logger)

        self._commands = Commands(self._config, self._client, self._data_logger)

    def _setup_logger(self):
        # Setup logger
        root = logging.getLogger()
        level = self._config['logger']['level']
        root.setLevel(level)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(level)
        formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
        ch.setFormatter(formatter)
        root.addHandler(ch)

    def initialise(self):
        logger.info('Initialising.')

        # Connect to MQTT
        self._client.on_connect = self._on_connect
        self._client.connect_async(host=self._config["mqtt"]["broker_host"],
                                   port=self._config["mqtt"]["broker_port"])
        self._client.loop_start()
        # Initialise controller
        self._controller.initialise()
        self._commands.init()

    def run(self):
        # Parse args (should probably be outside of this class really)
        parser = argparse.ArgumentParser()
        parser.add_argument('test-notifications', help='Tests push notifications')
        args = vars(parser.parse_args())
        if 'test-notifications' in args:
            self.test_notifications()
        else:
            self._go = True
            self._control_loop()

    def terminate(self):
        # Causes the control loop to stop
        self._go = False
        self._controller.stop()
        self._client.loop_stop()

        # We are done with GPIOs.
        GPIO.cleanup()
        # Terminates communications.
        self._client.disconnect()
        logger.info('Control loop terminated.')

    def _control_loop(self):
        logger.info('Running control loop.')
        pacer = Pacer()
        self._controller.start()
        try:
            while self._go:
                now = time.time()

                # Tick controller
                self._controller.tick(now)

                # Pace control loop per desired interval
                try:
                    pacer.pace(now, self._config['intervals']['control_loop_second'])
                except KeyboardInterrupt:
                    self._go = False
        finally:
            self.terminate()

    def _on_connect(self, client, userdata, flags, rc):
        logger.info('MQTT Connected with result code ' + str(rc))

        # Subscribe to our control topics now that we have a connection
        root_topic = self._config['mqtt']['root_topic'] + get_cpu_id() + "/#"
        client.subscribe(root_topic)

    def _on_disconnect(self, client, userdata, rc):
        logger.info('MQTT Disonnected with result code ' + str(rc))

    def test_notifications(self):
        from notifications.notify import push_all
        push_all(self._data_logger, 'BBQPi', 'Test Message!', data={'some data'})


if __name__ == "__main__":
    agent = Agent()
    agent.initialise()
    agent.run()
