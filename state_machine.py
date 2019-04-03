import logging
logger = logging.getLogger(__name__)


class StateContext:
    def __init__(self, state, temperatures):
        self.state = state
        self.temperatures = temperatures


class BBQStateMachine:
    """ Defines a generic state machine. """
    def __init__(self, ctx):
        self.current_states = {
            'probe1': SetPointInitial(),
            'probe2': SetPointInitial(),
        }
        self.ctx = ctx

    def run(self, timestamp):
        # Run states and transition, very simple
        for sensor in self.current_states.keys():
            self.current_states[sensor] = self.current_states[sensor].run(timestamp, self.ctx)


class SetPointInitial:
    def run(self, timestamp, ctx):
        logger.info('Setpoint initial')
        return self


class SetPointUnder:
    def run(self, timestamp, ctx):

        return self


class SetPointOver:
    def run(self, timestamp, ctx):

        return self


class SetPointOverAlarm:
    def run(self, timestamp, ctx):

        return self


class SetPointAlarmCancelled:
    def run(self, timestamp, ctx):

        return self

