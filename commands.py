import logging
import uuid
import json

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
        try:
            payload = message.payload.decode("utf-8")
            logger.info('Received config payload {}'.format(payload))

            if len(payload) > 0:
                cmd = json.loads(payload)
                print(cmd)

                ok = False
                if cmd['name'] == 'RegisterPushNotificationToken':
                    ok = self._handle_register_push_notification_token(cmd)
                else:
                    logger.warn('Received unexpected command in payload {}'.format(payload))
            
                # Now ack/nack response
                if ok:
                    self._client.publish(cmd['reply_topic'], json.dumps({'id': cmd['id'], 'response': 'ACK'}))
                else:
                    self._client.publish(cmd['reply_topic'], json.dumps({'id': cmd['id'], 'response': 'NACK'}))
        except Exception as ex:
            logger.error('Error processing inbound command', ex)

    def _handle_register_push_notification_token(self, cmd):
        token = cmd['token']
        logger.info('New push notification token {} received'.format(token))
        self._data_logger.save_push_tokens([token])
        return True
