import logging
import sys
import time

from settings import AgentConfig


class Agent:
    def __init__(self):
        self._config = AgentConfig()

    def main(self):
        self._initialise()
        self.run()

    def _initialise(self):
        root = logging.getLogger()
        root.setLevel(self._config.logger.level)

        # Setup logger
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(self._config.logger.level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        root.addHandler(ch)

        self.logger = logging.getLogger(self._config.logger.name)
        self.logger.info('Initialising.')

    def run(self):
        print("running")
        self._control_loop()

    def _control_loop(self):
        self.logger.info('Running control loop.')
        start_time = time.time()
        while True:
            self.logger.debug('Tick t={}'.format(start_time))

            # Pace control loop per desired interval
            sleep_time = self._config.control_loop_seconds - (time.time() - start_time)
            time.sleep(sleep_time)
            start_time = time.time()


if __name__ == "__main__":
    agent = Agent()
    agent.main()
