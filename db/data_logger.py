import sqlite3
import logging
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)

sensor_schema = """
CREATE TABLE IF NOT EXISTS sensor_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP,
    device_id STRING NOT NULL,
    sensor_name STRING NOT NULL,
    temp FLOAT NOT NULL,
    status STRING NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sensor_timestamp ON sensor_data (timestamp);

CREATE TABLE IF NOT EXISTS push_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token STRING NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    device_id STRING NOT NULL
);
"""

RETENTION_HOURS = 48


class DataLogger:
    def __init__(self, sqlite_file, device_id):
        self.device_id = device_id
        self.conn = sqlite3.connect(sqlite_file)
        self._check_schema()
        self._last_trim_datetime = None

    def _check_schema(self):
        logger.info('Setting Data Logger')
        self.conn.executescript(sensor_schema)
        self.conn.commit()
        logger.info('Data Logger ready');

    def log_sensors(self, timestamp, sensors):
        c = self.conn.cursor()
        for name, data in sensors:
            temp = data['temp']
            if temp is None:
                temp = -1
            c.execute(
                "INSERT INTO sensor_data (timestamp, device_id, sensor_name, temp, status) VALUES ({}, '{}', '{}', {}, '{}');". \
                format(timestamp, self.device_id, name, temp, data['status']))
        self.conn.commit()

        # Delete old entries periodically
        now = datetime.now()
        threshold = now - timedelta(hours=RETENTION_HOURS)
        if self._last_trim_datetime is None or threshold > self._last_trim_datetime:
            self.trim()
            self._last_trim_datetime = now

    def trim(self):
        logger.debug('Trimming data logger entries');
        c = self.conn.cursor()
        now = datetime.now()
        since = now - timedelta(hours=RETENTION_HOURS)
        epoch = time.mktime(since.timetuple())
        c.execute('DELETE FROM sensor_data WHERE timestamp < {};'.format(epoch))
        self.conn.commit()

    def push_tokens(self):
        """ Get all known push tokens registered under for this device"""
        c = self.conn.cursor()
        return c.execute("SELECT token FROM push_tokens WHERE device_id ='{}';".format(self.device_id)).fetchall()

    def save_push_tokens(self, tokens):
        """ Register push tokens for this device"""
        c = self.conn.cursor()
        for token in tokens:

            # First find out if this compbo exists
            count = c.execute("SELECT COUNT(*) FROM push_tokens WHERE device_id ='{}' AND token = '{}';".format(self.device_id, token)).fetchall()[0]
            if count[0] == 0:
                c.execute(
                    "INSERT INTO push_tokens (device_id, token) VALUES ('{}', '{}');".format(self.device_id, token))
        self.conn.commit()




