import logging

from exponent_server_sdk import DeviceNotRegisteredError
from exponent_server_sdk import PushClient
from exponent_server_sdk import PushMessage
from exponent_server_sdk import PushResponseError
from exponent_server_sdk import PushServerError
from requests.exceptions import ConnectionError
from requests.exceptions import HTTPError

logger = logging.getLogger(__name__)


def push_all(db, title, body, sound='default', data=None):
    is_ok = True
    for token in db.push_tokens():
        logger.info('Pushing {} to {}'.format(data, token))
        try:
            is_ok = send_push_message(token, title, body, sound, data) and is_ok
        except DeviceNotRegisteredError:
            # Delete token then
            db.delete_tokens([token])
    return is_ok


def send_push_message(token, title, body, sound, data=None):
    try:
        response = PushClient().publish(
            PushMessage(to=token,
                        title=title,
                        body=body,
                        sound=sound,
                        data=data))
    except PushServerError as exc:
        # Encountered some likely formatting/validation error.
        logger.error('Push Server error: '.format(exc.message))
        return False

    except (ConnectionError, HTTPError) as exc:
        # Encountered some Connection or HTTP error - retry a few times in
        # case it is transient.
        logger.error('Network error: '.format(exc.message))
        return False

    try:
        # We got a response back, but we don't know whether it's an error yet.
        # This call raises errors so we can handle them with normal exception
        # flows.
        response.validate_response()

    except PushResponseError as exc:
        # Encountered some other per-notification error.
        logger.error('Push Response Error: '.format(exc.message))
        return False

    return True
