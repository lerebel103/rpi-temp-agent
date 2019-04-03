import logging
from state_machine import State

logger = logging.getLogger(__name__)


class StoppedState(State):
    def run(self, timestamp, ctx):
        logger.info('StoppedState running')


class StartedState(State):
    def run(self, timestamp, ctx):
        logger.info('StartedState running')


