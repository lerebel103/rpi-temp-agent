import json
import logging
from enum import IntEnum
from json import JSONDecodeError

from memoized import memoized

from hardware_id import get_cpu_id
from peripherals.temperature_sensors import Max31850Sensors
from pid import PID
from notifications import notify
from state_machine import BBQStateMachine, StateContext

logger = logging.getLogger(__name__)


class Mode(IntEnum):
    """ Records the state of each temp sensor. """
    READY = 0,
    ACTIVE = 1,


class TempController:

    def __init__(self, config, sensors, blower_fan, client, data_logger):
        self._config = config
        self._client = client
        self._data_logger = data_logger
        self._pid = PID()
        self._temp_sensors = sensors
        self._blower_fan = blower_fan
        self._send_loop_count = 0
        self._state_machine = None

        # Load dynamic state configuration
        with open('config/state.json') as f:
            state = json.load(f)
        self._state = state

    def initialise(self):
        # Initialise peripherals
        self._temp_sensors.initialise()
        self._blower_fan.initisalise()

        # Subscribe to topics
        topic = self._config['mqtt']['root_topic'] + get_cpu_id() + "/controller/config/desired"
        self._client.message_callback_add(topic, self._message_config)
        logger.info('Subscribed to {}'.format(topic))

        # Subscribe to topics
        topic = self._config['mqtt']['root_topic'] + get_cpu_id() + "/controller/state/desired"
        self._client.message_callback_add(topic, self._message_state)
        logger.info('Subscribed to {}'.format(topic))

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
        pit_temp = self._temp_sensors.pit_temp
        probe1_temp = self._temp_sensors.probe1_temp
        # TODO
        probe2_temp = self._temp_sensors.probe2_temp

        # Read fan state
        rpm = self._blower_fan.rpm
        healthy = self._blower_fan.is_healthy

        # Calculate duty cycle
        duty_cycle = 0
        if self._state['mode'] == Mode.ACTIVE:
            if pit_temp['status'] == Max31850Sensors.Status.OK:
                duty_cycle = self._pid.update(now, pit_temp['temp'])
                duty_cycle += self._config['controller']['blower_cycle_min']
                duty_cycle = max(duty_cycle, self._config['controller']['blower_cycle_min'])
                duty_cycle = min(duty_cycle, self._config['controller']['blower_cycle_max'])

            # Set fan duty cycle and collect RPM
            self._blower_fan.duty_cycle = duty_cycle
            self._blower_fan.on()  # Always make sure fan is on
 
            # Tick state machine
            if self._state_machine == None:
                self._state_machine = BBQStateMachine()
            ctx = StateContext(now, self._state, self._temp_sensors)
            self._state_machine.run(ctx)
        else:
            self._blower_fan.off()  # Always make sure fan is off
            self._state_machine = None

        # Publish data
        if self._send_loop_count == 0:
            # MQTT
            self._client.publish(self.topic + "/temperature/board", json.dumps({'temp': self._temp_sensors.board_temp}))
            self._client.publish(self.topic + "/temperature/probe1", json.dumps(probe1_temp))
            self._client.publish(self.topic + "/temperature/probe2", json.dumps(probe2_temp))
            self._client.publish(self.topic + "/temperature/pit", json.dumps(pit_temp))
            self._client.publish(self.topic + "/fan", json.dumps({'dutyCycle': duty_cycle, 'rpm': rpm, 'healthy': healthy}))
            logger.debug('pit={}, probe={}, rpm={}, duty={}'.format(pit_temp, probe1_temp, rpm, duty_cycle))

            # data logger
            temps = [
                    ('probe1', probe1_temp),
                    ('probe2', probe2_temp),
                    ('pit', pit_temp),
                    ('board', {'temp': self._temp_sensors.board_temp, 'status': 'OK'})
            ]
            self._data_logger.log_sensors(now, temps)

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

                # Save config
                with open('config/config.json', 'w') as f:
                    json.dump(self._config, f, indent=4, sort_keys=True)

                # Send config back as reply
                config = json.dumps(self._config['controller'])
                self._client.publish(root_topic + "/controller/config/reported", config)
            except JSONDecodeError as ex:
                logger.error("Inbound payload isn't JSON: {}".format(ex.msg))
        else:
            # Send config back as reply
            config = json.dumps(self._config['controller'])
            self._client.publish(root_topic + "/controller/config/reported", config)

    def _message_state(self, mosq, obj, message):
        root_topic = self.topic
        payload = message.payload.decode("utf-8")
        logger.info('Received state payload {}'.format(payload))

        if len(payload) > 0:
            try:
                desired = json.loads(payload)
                # TODO We need to validate first, use schema validation

                # Now merge
                self._state = {**self._state, **desired}
                self._update_pid_params()

                # Save state
                with open('config/state.json', 'w') as f:
                    json.dump(self._state, f, indent=4, sort_keys=True)
                # Send state back as reply
                state = json.dumps(self._state)
                self._client.publish(root_topic + "/controller/state/reported", state)

            except JSONDecodeError as ex:
                logger.error("Inbound payload isn't JSON: {}".format(ex.msg))
        else:
            # Send state back as reply
            state = json.dumps(self._state)
            self._client.publish(root_topic + "/controller/state/reported", state)

    @property
    @memoized
    def topic(self):
        root_topic = self._config['mqtt']['root_topic'] + get_cpu_id()
        return root_topic

    def _update_pid_params(self):
        self._pid.Kp = self._config['controller']['P']
        self._pid.Ki = self._config['controller']['I']
        self._pid.Kd = self._config['controller']['D']
        self._pid.set_point = self._state['pit']['setPoint']
