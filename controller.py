import json
import logging
from enum import IntEnum
from json import JSONDecodeError

from memoized import memoized

from hardware_id import get_cpu_id
from peripherals.temperature_sensors import Max31850Sensors
from pid import PID
from state_machine.sm import BBQStateMachine
from state_machine.state_context import StateContext, DEFAULT_ACCUMULATORS

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

        # Setup accumulators
        self._accumulators = DEFAULT_ACCUMULATORS

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
        # Spin through all sensors and control the the thing
        temps = []
        for sensor_name in self._accumulators:
            sensor_state = self._temp_sensors.sensor_temp(sensor_name)
            if sensor_state['status'] == Max31850Sensors.Status.OK:
                temp = sensor_state['temp']
                # Start by accumulating values over time
                self._accumulators[sensor_name].add(now, temp)
                temps.append((sensor_name, sensor_state))

                if sensor_name == 'pit':
                    self._control_pit(now, temp)

            # Publish data for these sensors
            if self._send_loop_count == 0:
                topic = self.topic + '/temperature/{}'.format(sensor_name)
                self._client.publish(topic, json.dumps(sensor_state))

        # Tick state machine
        if self._state['mode'] == Mode.ACTIVE:
            if self._state_machine is None:
                self._state_machine = BBQStateMachine()
            ctx = StateContext(now, self._state, self._temp_sensors, accumulators=self._accumulators,
                               db=self._data_logger)
            self._state_machine.run(ctx)
        else:
            self._state_machine = None

        # Publish and log more data
        if self._send_loop_count == 0:
            # Publish temp of board itself
            self._client.publish(self.topic + "/temperature/board", json.dumps({'temp': self._temp_sensors.board_temp}))

            # Data log the entire set
            temps.append(('board', {'temp': self._temp_sensors.board_temp, 'status': 'OK'}))
            self._data_logger.log_sensors(now, temps)

        self._send_loop_count += 1
        if self._send_loop_count > self._config['controller']['send_data_loop_count']:
            self._send_loop_count = 0

    def _control_pit(self, now, pit_temp):
        # Calculate duty cycle
        duty_cycle = 0
        if self._state['mode'] == Mode.ACTIVE:
            duty_cycle = self._pid.update(now, pit_temp)
            duty_cycle += self._config['controller']['blower_cycle_min']
            duty_cycle = max(duty_cycle, self._config['controller']['blower_cycle_min'])
            duty_cycle = min(duty_cycle, self._config['controller']['blower_cycle_max'])

            # Set fan duty cycle and collect RPM
            self._blower_fan.duty_cycle = duty_cycle
            self._blower_fan.on()  # Always make sure fan is on
        else:
            self._blower_fan.off()  # Always make sure fan is off

        if self._send_loop_count == 0:
            # Publish Fan state
            self._client.publish(self.topic + "/fan",
                                 json.dumps({
                                     'dutyCycle': duty_cycle,
                                     'rpm': self._blower_fan.rpm,
                                     'healthy': self._blower_fan.is_healthy}))

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
