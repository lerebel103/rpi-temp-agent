import logging

import DS18B20 as DS

logger = logging.getLogger(__name__)


class TempSensors:

    def __init__(self, gpio_pin):
        self._pin = gpio_pin
        self._sensors = None

    def initialise(self):
        self._sensors = DS.scan(self._pin)
        logger.info('Found temperature sensors with ids {}'.format(self._sensors))
        DS.pinsStartConversion([self._pin])

    def tick(self, tick_time):
        for sensor in self._sensors:
            temps = DS.readMax31850(False, self._pin, sensor)
            print(temps)

        # Start the conversion for the next loop
        logger.info('Start Conversion on pin {}'.format(self._pin))
        DS.pinsStartConversion([self._pin])

