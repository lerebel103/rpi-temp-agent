import json
import logging

from memoized import memoized

from hardware_id import get_cpu_id
from peripherals.temperature_sensors import Max31850Sensors
from pid import PID

logger = logging.getLogger(__name__)


class TempController:

    def __init__(self, config, sensors, blower_fan, client):
        self._config = config
        self._client = client
        self._pid = PID()
        self._temp_sensors = sensors
        self._blower_fan = blower_fan
        self._send_loop_count = 0

    def initialise(self):
        # Initialise peripherals
        self._temp_sensors.initialise()
        self._blower_fan.initisalise()

        # Subscribe to topics
        topic = self._config['mqtt']['root_topic'] + get_cpu_id() + "/controller/config"
        self._client.message_callback_add(topic, self._message_config)

    def start(self):
        logger.info('Controller starting.')
        self._send_loop_count = 0
        self._blower_fan.on()
        self._temp_sensors.on()

    def stop(self):
        self._temp_sensors.off()
        self._blower_fan.off()
        logger.info('Controller stopped.')

    def tick(self, now):
        # Read sensor temps and publish
        sensor = self._config['controller']['sensors_ids']['bbq']
        bbq_temp = self._temp_sensors.sensor_temp(sensor)

        sensor = self._config['controller']['sensors_ids']['food']
        food_temp = self._temp_sensors.sensor_temp(sensor)

        # Calculate duty cycle
        duty_cycle = 0
        if bbq_temp['status'] == Max31850Sensors.Status.OK:
            duty_cycle = self._pid.update(now, bbq_temp['temp'])
            duty_cycle = max(duty_cycle, self._config['controller']['blower_cycle_min'])
            duty_cycle = min(duty_cycle, self._config['controller']['blower_cycle_max'])

        # Set fan duty cycle and collect RPM
        self._blower_fan.duty_cycle = duty_cycle
        rpm = self._blower_fan.rpm
        healthy = self._blower_fan.is_healthy

        # Publish data
        if self._send_loop_count == 0:
            self._client.publish(self.topic + "/food", json.dumps(food_temp))
            self._client.publish(self.topic + "/bbq", json.dumps(bbq_temp))
            self._client.publish(self.topic + "/fan", json.dumps({'duty_cycle': duty_cycle, 'rpm': rpm, 'healthy': healthy}))
            logger.debug('bbq={}, food={}, rpm={}, duty={}'.format(bbq_temp, food_temp, rpm, duty_cycle))

        self._send_loop_count += 1
        if self._send_loop_count > self._config['controller']['send_data_loop_count']:
            self._send_loop_count = 0

    def _message_config(self, mosq, obj, message):
        root_topic = self.topic
        payload = message.payload.decode("utf-8")
        logger.info('Received config payload {}'.format(payload))

        # Send config back as reply
        config = json.dumps(self._config['controller'])
        self._client.publish(root_topic + "/food", config)

    @property
    @memoized
    def topic(self):
        root_topic = self._config['mqtt']['root_topic'] + get_cpu_id()
        return root_topic

