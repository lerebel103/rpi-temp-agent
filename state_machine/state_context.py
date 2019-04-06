from accumulator import Accumulator
from state_machine.probe_states import SetPointInitial
from state_machine.pit_states import PitInitial

DEFAULT_ACCUMULATOR_PERIOD = 10*60  # in seconds

DEFAULT_ACCUMULATORS = {
    'pit': Accumulator(DEFAULT_ACCUMULATOR_PERIOD),
    'probe1': Accumulator(DEFAULT_ACCUMULATOR_PERIOD),
    'probe2': Accumulator(DEFAULT_ACCUMULATOR_PERIOD),
}


class StateContext:
    probe_init_state_class = SetPointInitial
    pit_init_state_class = PitInitial

    def __init__(self, timestamp, user_config, temperatures, accumulators=DEFAULT_ACCUMULATORS, db=None):
        self.timestamp = timestamp
        self.user_config = user_config
        self.temperatures = temperatures
        self.accumulators = accumulators
        self.db = db
