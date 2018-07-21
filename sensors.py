import logging

import DS18B20 as DS

logger = logging.getLogger(__name__)


class TempSensors:

    def __init__(self, gpio_pin):
        self._pin = gpio_pin
        self._sensors = None
        self._board_temp = None
        self._temps = dict()

    def initialise(self):
        self._sensors = DS.scan(self._pin)
        logger.info('Found temperature sensors with ids {}'.format(self._sensors))
        DS.pinsStartConversion([self._pin])

    @property
    def sensors(self):
        return self._sensors

    @property
    def board_temp(self):
        return self._board_temp

    @property
    def sensor_temp(self, sensor):
        return self._temps[sensor]

    def tick(self):
        board_temps = 0
        for sensor in self._sensors:
            temps = DS.readMax31850(False, self._pin, sensor)
            self._temps[sensor] = temps[0]
            board_temps += temps[1]
            # There is a third element, not sure what we could do with that.

        if len(self._sensors) > 0
            self._board_temp = board_temps / len(self._sensors)

        # Start the conversion for the next loop
        logger.debug('Start Conversion on pin {}'.format(self._pin))
        DS.pinsStartConversion([self._pin])

