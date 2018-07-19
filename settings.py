

class MqttConfig:
    client_id = str(__name__)
    host = 'localhost'
    port = 1883


class LoggerConfig:
    name = 'rpi-temp-agent'
    level = 'DEBUG'


class AgentConfig:

    mqtt = MqttConfig()
    logger = LoggerConfig()
    control_loop_seconds = 0.5
