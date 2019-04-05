import logging

from state_machine.state_context import StateContext

logger = logging.getLogger(__name__)


class BBQStateMachine:

    """ Defines the top level state machine for all sensors. """
    def __init__(self):
        self.current_states = {}
        self.reset()

    def reset(self):
        logger.info('Resetting state machine')
        self.current_states = {
            'pit': StateContext.pit_init_state_class(),
            'probe1': StateContext.probe_init_state_class(),
            'probe2': StateContext.probe_init_state_class(),
        }

    def run(self, ctx):
        # Run states and transition, very simple
        for sensor in self.current_states.keys():
            self.current_states[sensor] = self.current_states[sensor].run(sensor, ctx)




