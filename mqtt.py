import paho.mqtt.client as mqtt_client

class MqttComms:

    def __init__(self, client_name, host, port):
        self._client = mqtt_client.Client(client_id=client_name)
        self._host = host
        self._port = port

    def start(self):
        self._client.connect(host=self._host, port=self._port)

