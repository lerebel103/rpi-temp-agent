import logging
import threading
from time import time, sleep
from enum import Enum

import DS18B20 as DS

logger = logging.getLogger(__name__)


class Max31850Sensors:
    """ Wrapper around DS18B20 to provide an adapter for the Max31850 boards.

    """

    class Status(Enum):
        """ Records the state of each temp sensor. """
        UNKNOWN = -1,
        OK = 0,
        OPEN_CIRCUIT = 1,
        SHORT_TO_GROUND = 2,
        SHORT_TO_VDD = 4

    def __init__(self, gpio_pin, temp_sample_interval):
        """ We need to bind this instance to a specific 1-wire gpio, as given to this class.

        :param gpio_pin: GPIO pin to which the Max31850 data ports are attached.
        """
        self._pin_1wire = gpio_pin
        self._temp_sample_interval = temp_sample_interval
        self.is_on = False
        self._sensors = None
        self._board_temp = None
        self._temps = dict()
        self._update_thread = None

    def initialise(self):
        self.off()

        self._sensors = DS.scan(self._pin_1wire)
        logger.info('Found temperature sensors with ids {}'.format(self._sensors))

        # Preload reading with initial state.
        for sensor in self._sensors:
            self._temps[sensor] = {'temp': None, 'status': Max31850Sensors.Status.UNKNOWN}

        self._update_thread = threading.Timer(0, self._update_loop)
        self._update_thread.daemon = True
        logger.info('Initialised Temperature sensors on gpio {}'.format(self._pin_1wire))

    def on(self):
        """ Start temperature reading in a background thread. """
        if not self.is_on:
            self.is_on = True
            self._update_thread.start()
            logger.info('Started Temperature reading on gpio {}'.format(self._pin_1wire))

    def off(self):
        """ Stop temperature reading in a background thread. """
        if self.is_on:
            self._update_thread.cancel()
            self.is_on = False
            logger.info('Stopped Temperature reading on gpio {}'.format(self._pin_1wire))

    @property
    def sensors(self):
        """ \:returns List of sensors discovered by the system. """
        return self._sensors

    def sensor_temp(self, sensor):
        """ \:returns Returns a tuple as (temp, status). """
        return self._temps[sensor]['temp'], self._temps[sensor]['status'],

    def board_temp(self):
        """ Single value if a board temp was available (status was ok).

        \:returns Single value for board temperature, or None.
        """
        return self._board_temp

    def _update_loop(self):
        """ Continue to read temps in a loop until asked to stop. """
        while self.is_on:
            # Start the conversion for the next loop
            logger.debug('Start Conversion on pin {}'.format(self._pin_1wire))
            DS.pinsStartConversion([self._pin_1wire])

            # Requires sleep for samples to appear
            sleep(self._temp_sample_interval)

            # We can average out the board temperature for this device, nice indicator.
            board_temps = 0
            for sensor in self._sensors:
                temps = DS.readMax31850(False, self._pin_1wire, sensor)

                # First we get our status, as we need to decide if this reading is going to be valid.
                status = self._do_status(temps)
                if status == Max31850Sensors.Status.OK:
                    # Good, then we get the temperature reported by the 1-wire device
                    logger.debug('Sensor {} reports a valid temperature as {}'.format(sensor, temps[0]))
                    self._temps[sensor]['temp'] = temps[0]
                    self._temps[sensor]['status'] = status
                    board_temps += temps[1]
                else:
                    # This is not good then, whatever the case is, we can't trust this temp
                    logger.debug('Sensor {} reports an error as {}'.format(sensor, status))
                    self._temps[sensor]['temp'] = temps[0]  # This may be rubbish at this point
                    self._temps[sensor]['status'] = status

            # Now we can get the mean of our board temps.
            if len(self._sensors) > 0:
                self._board_temp = board_temps / len(self._sensors)

    @staticmethod
    def _do_status(temps):
        """ Work out the status of this sensor. """
        flags = temps[2]
        if flags == 0:
            return Max31850Sensors.Status.OK
        elif flags & 2:
            # Open circuit
            return Max31850Sensors.Status.OPEN_CIRCUIT
        elif flags & 4:
            # Short to ground
            return Max31850Sensors.Status.SHORT_TO_GROUND
        elif flags & 8:
            # Short to VDD
            return Max31850Sensors.Status.SHORT_TO_VDD
        else:
            # No idea then, but it can't be good.
            return Max31850Sensors.Status.UNKNOWN
