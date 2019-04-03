
class StateContext:
    pass


class BBQStateMachine:
    """ Defines a generic state machine. """
    def __init__(self, initial_state, ctx):
        self.current_state = initial_state
        self.ctx = ctx

    def run(self, timestamp):
        """ Run forever, and allow state transitions to take place as a chain. """
        while self.current_state is not None:
            self.current_state = self.current_state.run(timestamp, self.ctx)


class State:
    """
    Defines a State has an operation, and can be moved
    into the next State given an Input:
    """

    def run(self, timestamp, ctx):
        assert 0, 'run not implemented'
