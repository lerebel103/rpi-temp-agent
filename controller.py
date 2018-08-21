import json
import logging
from enum import IntEnum
from json import JSONDecodeError

from memoized import memoized

from hardware_id import get_cpu_id
from peripherals.temperature_sensors import Max31850Sensors
from pid import PID

logger = logging.getLogger(__name__)


class State(IntEnum):
    """ Records the state of each temp sensor. """
    READY = 0,
    ACTIVE = 1,


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
        topic = self._config['mqtt']['root_topic'] + get_cpu_id() + "/controller/config/desired"
        self._client.message_callback_add(topic, self._message_config)

        # Set pid params initially
        self._update_pid_params()

    def start(self):
        logger.info('Controller starting.')
        self._send_loop_count = 0
        self._temp_sensors.on()

    def stop(self):
        self._temp_sensors.off()
        self._blower_fan.off()
        logger.info('Controller stopped.')

    def tick(self, now):
        # Read sensor temps and publish
        bbq_temp = self._temp_sensors.bbq_temp
        food_temp = self._temp_sensors.food_temp

        # Read fan state
        rpm = self._blower_fan.rpm
        healthy = self._blower_fan.is_healthy

        # Calculate duty cycle
        duty_cycle = 0
        if self._config['controller']['state'] == State.ACTIVE:
            if bbq_temp['status'] == Max31850Sensors.Status.OK:
                duty_cycle = self._pid.update(now, bbq_temp['temp'])
                duty_cycle += self._config['controller']['blower_cycle_min']
                duty_cycle = max(duty_cycle, self._config['controller']['blower_cycle_min'])
                duty_cycle = min(duty_cycle, self._config['controller']['blower_cycle_max'])

            # Set fan duty cycle and collect RPM
            self._blower_fan.duty_cycle = duty_cycle
            self._blower_fan.on()  # Always make sure fan is on
        else:
            self._blower_fan.off()  # Always make sure fan is off

        # Publish data
        if self._send_loop_count == 0:
            self._client.publish(self.topic + "/temperature/board", json.dumps({'temp': self._temp_sensors.board_temp}))
            self._client.publish(self.topic + "/temperature/food", json.dumps(food_temp))
            self._client.publish(self.topic + "/temperature/bbq", json.dumps(bbq_temp))
            self._client.publish(self.topic + "/fan", json.dumps({'duty_cycle': duty_cycle, 'rpm': rpm, 'healthy': healthy}))
            logger.debug('bbq={}, food={}, rpm={}, duty={}'.format(bbq_temp, food_temp, rpm, duty_cycle))

        self._send_loop_count += 1
        if self._send_loop_count > self._config['controller']['send_data_loop_count']:
            self._send_loop_count = 0

    def _message_config(self, mosq, obj, message):
        root_topic = self.topic
        payload = message.payload.decode("utf-8")
        logger.info('Received config payload {}'.format(payload))

        if len(payload) > 0:
            try:
                desired = json.loads(payload)
                # TODO We need to validate first, use schema validation

                # Now merge
                self._config['controller'] = {**self._config['controller'], **desired}
                self._update_pid_params()
            except JSONDecodeError as ex:
                logger.error("Inbound payload isn't JSON: {}".format(ex.msg))

        # Send config back as reply
        config = json.dumps(self._config['controller'])
        self._client.publish(root_topic + "/controller/config/reported", config)

    @property
    @memoized
    def topic(self):
        root_topic = self._config['mqtt']['root_topic'] + get_cpu_id()
        return root_topic

    def _update_pid_params(self):
        self._pid.Kp = self._config['controller']['P']
        self._pid.Ki = self._config['controller']['I']
        self._pid.Kd = self._config['controller']['D']
        self._pid.set_point = self._config['controller']['temperature_set_point']
