

class MqttConfig:
    client_id = str(__name__)
    host = 'raspberrypi.local'
    port = 1883


class LoggerConfig:
    level = 'INFO'


class AgentConfig:
    mqtt = MqttConfig()

    logger = LoggerConfig()

    temperature_gpio = 4

    blower_fan_gpio_pwm = 12

    blower_fan_gpio_relay = 5

    blower_fan_gpio_rpm = 6

    control_loop_seconds = 1
