import logging

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

    def initialise(self):
        # Initialise peripherals
        self._temp_sensors.initialise()
        self._blower_fan.initisalise()

    def start(self):
        logger.info('Controller starting.')
        self._blower_fan.on()
        self._temp_sensors.on()

    def stop(self):
        self._temp_sensors.off()
        self._blower_fan.off()
        logger.info('Controller stopped.')

    def tick(self, now):
        # Read sensor temps
        bbq_temp = None
        temps = ''
        for sensor in self._temp_sensors.sensors:
            temp, status = self._temp_sensors.sensor_temp(sensor)
            if temp is not None and status == Max31850Sensors.Status.OK:
                bbq_temp = temp
                temps += '[{:.3f}, {}] '.format(temp, status)
            else:
                bbq_temp = None
                temps += '[--, {}] '.format(status)

        if bbq_temp is not None:
            output = self._pid.update(now, bbq_temp)
            # Set fan duty cycle
            print(output)
            self._blower_fan.duty_cycle = output

        rpm = self._blower_fan.rpm

        if not self._blower_fan.is_healthy:
            print("**************** FAN NOT SPINNING.")

        # Tick all parts of the system from here
        msg = 'rpm={} temps={}, board={}'.format(rpm, temps, self._temp_sensors.board_temp())
        self._client.publish('test', msg, qos=1)

        logger.info(msg)
