from state_machine.probe_states import SetPointInitial
from state_machine.pit_states import PitInitial


class StateContext:
    probe_init_state_class = SetPointInitial
    pit_init_state_class = PitInitial

    def __init__(self, timestamp, state, temperatures, db=None):
        self.timestamp = timestamp
        self.state = state
        self.temperatures = temperatures
        self.db = db


