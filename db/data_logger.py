import sqlite3
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


sensor_schema="""
CREATE TABLE IF NOT EXISTS sensor_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP,
    source_id STRING NOT NULL,
    sensor_name STRING NOT NULL,
    temp FLOAT NOT NULL,
    status STRING NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sensor_timestamp ON sensor_data (timestamp);
"""

RETENTION_HOURS = 48

class DataLogger:
    def __init__(self, sqlite_file, source_id):
        self.source_id = source_id
        self.conn = sqlite3.connect(sqlite_file)
        self._check_schema()

    def _check_schema(self):
        logger.info('Setting Data Logger');
        self.conn.executescript(sensor_schema)
        self.conn.commit()
        logger.info('Data Logger ready');

    def log_sensors(self, timestamp, sensors):
        c = self.conn.cursor()
        for name, data in sensors:
            temp = data['temp']
            if temp is None:
                temp = -1
            c.execute("INSERT INTO sensor_data (timestamp, source_id, sensor_name, temp, status) VALUES ({}, '{}', '{}', {}, '{}')".\
                    format(timestamp, self.source_id, name, temp, data['status']))
        self.conn.commit()
        self.trim()

    def trim(self):
        c = self.conn.cursor()
        now = datetime.now()
        since = now - timedelta(hours=RETENTION_HOURS)
        print(since)
        c.execute('DELETE FROM sensor_data WHERE timestamp < {});'.format(since.epoch()))
        self.conn.commit()

