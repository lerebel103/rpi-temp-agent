#!/usr/bin/env python
import logging
import sys
import time

import paho.mqtt.client as mqtt_client

from config import AgentConfig
from pacer import Pacer
from sensors import Max31850Sensors

logger = logging.getLogger(__name__)


class Agent:
    def __init__(self):
        self._config = AgentConfig()
        self._go = False
        self._temp_sensors = Max31850Sensors(self._config.temperature_gpio)

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

        # Initialise temp sensors
        self._temp_sensors.initialise()
        # Connect to MQTT
        self._client.connect_async(host=self._config.mqtt.host, port=self._config.mqtt.port)
        # Start control loop
        self._client.loop_start()

    def run(self):
        self._go = True
        self._control_loop()
        self._client.disconnect()

    def terminate(self):
        self._go = False
        self._client.loop_stop()

    def _control_loop(self):
        logger.info('Running control loop.')
        pacer = Pacer()
        while self._go:
            now = time.time()

            # Tick temp sensors
            self._temp_sensors.tick(now)
            temps = ''
            for sensor in self._temp_sensors.sensors:
                temp, status = self._temp_sensors.sensor_temp(sensor)
                temps += '[{:.3f}, {}] '.format(temp, status)

            # Tick all parts of the system from here
            msg = 'temps={}, board={}, time={}'.format(temps, self._temp_sensors.board_temp(), now)
            self._client.publish('test',msg , qos=1)

            logger.info(msg)
            # Pace control loop per desired interval
            try:
                pacer.pace(now, self._config.control_loop_seconds)
            except KeyboardInterrupt:
                self.terminate()

        logger.info('Control loop terminated.')


if __name__ == "__main__":
    agent = Agent()
    agent.initialise()
    agent.run()
