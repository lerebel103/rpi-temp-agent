import logging

from peripherals.temperature_sensors import Max31850Sensors
from state_machine.common_states import BaseSensorState

logger = logging.getLogger(__name__)

class PitInitial(BaseSensorState):
    def handle_temp(self, temp, set_point):
        if temp < set_point:
            return self
        else:
            return self 

