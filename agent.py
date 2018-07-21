import logging
import sys
import time

import paho.mqtt.client as mqtt_client

from config import AgentConfig
from pacer import Pacer
from sensors import TempSensors

logger = logging.getLogger(__name__)


class Agent:
    def __init__(self):
        self._config = AgentConfig()
        self._go = False
        self._temp_sensors = TempSensors(self._config.temperature_gpio)

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
            logger.debug('Tick t={}'.format(now))

            # Tick temp sensors
            self._temp_sensors.tick(now)

            # Tick all parts of the system from here
            self._client.publish("test", "hello " + str(now), qos=1)

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
