import logging

from state_machine.common_states import BaseSensorState

logger = logging.getLogger(__name__)


class PitInitial(BaseSensorState):
    def handle_temp(self, temp, set_point):
        if temp < set_point:
            return ComingToTemp()
        else:
            return OverTemp()


class ComingToTemp(BaseSensorState):
    def handle_temp(self, temp, set_point):

        last_minute = self.ctx.timestamp - 60
        print(temp)
        print('** derivative ' +
              str(self.ctx.accumulators[self.sensor_name].linear_derivative(last_minute)))

        return self


class UpToTemp(BaseSensorState):
    def handle_temp(self, temp, set_point):
        return self


class OverTemp(BaseSensorState):
    def handle_temp(self, temp, set_point):    
        print('over temp')
        return self


class LidOpen(BaseSensorState):
    def handle_temp(self, temp, set_point):
        return self


class FlameOut(BaseSensorState):
    def handle_temp(self, temp, set_point):
        return self
