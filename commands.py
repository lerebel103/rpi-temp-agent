import logging

from hardware_id import get_cpu_id

logger = logging.getLogger(__name__)


class Commands:
    def __init__(self, config, client, data_logger):
        self._config = config
        self._client = client
        self._data_logger = data_logger

    def init(self):
        # Setup command topic
        topic = self._config['mqtt']['root_topic'] + get_cpu_id() + "/commands"
        self._client.message_callback_add(topic, self._handle_message)
        logger.info('Subscribed to {}'.format(topic))

    def _handle_message(self, mosq, obj, message):
        payload = message.payload.decode("utf-8")
        logger.info('Received config payload {}'.format(payload))

        if len(payload) > 0:
            print('got message')