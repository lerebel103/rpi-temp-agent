

class MqttConfig:
    client_id = str(__name__)
    host = 'raspberrypi.local'
    port = 1883


class LoggerConfig:
    level = 'DEBUG'


class AgentConfig:
    mqtt = MqttConfig()
    logger = LoggerConfig()
    control_loop_seconds = 1
