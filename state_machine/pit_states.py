import logging

from state_machine.common_states import BaseSensorState

logger = logging.getLogger(__name__)


class PitInitial(BaseSensorState):
    def handle_temp(self, temp, set_point):
        if temp < set_point:
            return self
        else:
            return self


class ComingToTemp(BaseSensorState):
    def handle_temp(self, temp, set_point):
        return self


class UpToTemp(BaseSensorState):
    def handle_temp(self, temp, set_point):
        return self


class OverTemp(BaseSensorState):
    def handle_temp(self, temp, set_point):
        return self


class LidOpen(BaseSensorState):
    def handle_temp(self, temp, set_point):
        return self


class FlameOut(BaseSensorState):
    def handle_temp(self, temp, set_point):
        return self
