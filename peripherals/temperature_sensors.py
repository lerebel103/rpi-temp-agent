import logging
import sys
import threading
from time import time, sleep
from enum import Enum, IntEnum
from copy import deepcopy

import DS18B20 as DS

logger = logging.getLogger(__name__)


class Max31850Sensors:
    """ Wrapper around DS18B20 to provide an adapter for the Max31850 boards.

    """

    class Status(IntEnum):
        """ Records the state of each temp sensor. """
        UNKNOWN = -1,
        OK = 0,
        OPEN_CIRCUIT = 1,
        SHORT_TO_GROUND = 2,
        SHORT_TO_VDD = 4

    def __init__(self, config):
        """ We need to bind this instance to a specific 1-wire gpio, as given to this class.

        :param gpio_pin: GPIO pin to which the Max31850 data ports are attached.
        """
        self._config = config
        self.is_on = False
        self._sensors = None
        self._board_temp = None
        self._temps = dict()
        self._update_thread = None

    def initialise(self):
        self.off()

        self._sensors = DS.scan(self._config['gpio'])
        if len(self._sensors) == 0:
            msg = 'No temperature sensors found, cowardly exiting.'
            logger.error(msg)
            sys.exit(msg)

        logger.info('Found temperature sensors with ids {}'.format(self._sensors))

        # Preload reading with initial state.
        for sensor in self._sensors:
            self._temps[sensor] = {'temp': None, 'status': Max31850Sensors.Status.UNKNOWN}

        self._update_thread = threading.Timer(0, self._update_loop)
        self._update_thread.daemon = True
        logger.info('Initialised Temperature sensors on gpio {}'.format(self._config['gpio']))

    def on(self):
        """ Start temperature reading in a background thread. """
        if not self.is_on:
            self.is_on = True
            self._update_thread.start()
            logger.info('Started Temperature reading on gpio {}'.format(self._config['gpio']))

    def off(self):
        """ Stop temperature reading in a background thread. """
        if self.is_on:
            self._update_thread.cancel()
            self.is_on = False
            logger.info('Stopped Temperature reading on gpio {}'.format(self._config['gpio']))

    @property
    def sensors(self):
        """ \:returns List of sensors discovered by the system. """
        return self._sensors

    @property
    def probe1_temp(self):
        """ \:returns Returns a tuple as (temp, status) for probe1. """
        conf = self._config['probe1']
        return self._get_temp(conf)

    @property
    def probe2_temp(self):
        """ \:returns Returns a tuple as (temp, status) for probe2. """
        conf = self._config['probe2']
        return self._get_temp(conf)

    @property
    def pit_temp(self):
        """ \:returns Returns a tuple as (temp, status) for bbq. """
        conf = self._config['pit']
        return self._get_temp(conf)

    @property
    def board_temp(self):
        """ Single value if a board temp was available (status was ok).

        \:returns Single value for board temperature, or None.
        """
        if self._board_temp is not None:
            return self._board_temp + self._config['board']['temperature_offset']
        else:
            return None

    def sensor_temp(self, name):
        """ \:returns Returns a tuple as (temp, status) for a name. """
        conf = self._config[name]
        return self._get_temp(conf)

    def _get_temp(self, conf):
        if conf['id'] in self._temps:
            sensor_info = deepcopy(self._temps[conf['id']])
            if sensor_info['temp'] is not None:
                sensor_info['temp'] = sensor_info['temp'] + conf['temperature_offset']
            return sensor_info
        else:
            return {'temp': None, 'status': Max31850Sensors.Status.UNKNOWN}

    def _update_loop(self):
        """ Continue to read temps in a loop until asked to stop. """
        while self.is_on:
            # Start the conversion for the next loop
            logger.debug('Start Conversion on pin {}'.format(self._config['gpio']))
            DS.pinsStartConversion([self._config['gpio']])

            # Requires sleep for samples to appear
            sleep(self._config['sampling_seconds'])

            # We can average out the board temperature for this device, nice indicator.
            board_temps = 0
            count_board_ok = 0
            for sensor in self._sensors:
                temps = DS.readMax31850(False, self._config['gpio'], sensor)
                if temps is None:
                    continue

                # First we get our status, as we need to decide if this reading is going to be valid.
                status = self._do_status(temps, sensor)
                if status == Max31850Sensors.Status.OK:
                    # Good, then we get the temperature reported by the 1-wire device
                    logger.debug('Sensor {} reports a valid temperature as {}'.format(sensor, temps[0]))
                    self._temps[sensor]['temp'] = temps[0]
                    self._temps[sensor]['status'] = status
                    board_temps += temps[1]
                    count_board_ok += 1
                else:
                    # This is not good then, whatever the case is, we can't trust this temp
                    logger.debug('Sensor {} reports an error as {}'.format(sensor, status))
                    self._temps[sensor]['temp'] = None
                    self._temps[sensor]['status'] = status

            # Now we can get the mean of our board temps.
            if count_board_ok > 0:
                self._board_temp = board_temps / count_board_ok

    @staticmethod
    def _do_status(temps, sensor):
        """ Work out the status of this sensor. """
        flags = temps[2]
        if flags == 0:
            return Max31850Sensors.Status.OK
        elif flags & 2:
            # Open circuit
            return Max31850Sensors.Status.OPEN_CIRCUIT
        elif flags & 4:
            # Short to ground
            # return Max31850Sensors.Status.SHORT_TO_GROUND
            return Max31850Sensors.Status.OK
        elif flags & 8:
            # Short to VDD
            return Max31850Sensors.Status.SHORT_TO_VDD
        else:
            # No idea then, but it can't be good.
            return Max31850Sensors.Status.UNKNOWN
