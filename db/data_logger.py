import sqlite3
import logging

logger = logging.getLogger(__name__)


sensor_schema="""
CREATE TABLE IF NOT EXISTS sensor_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sensor_name STRING NOT NULL,
    temp FLOAT NOT NULL,
    status STRING NOT NULL
);
"""

class DataLogger:
    def __init__(self, sqlite_file):
        self.conn = sqlite3.connect(sqlite_file)
        self._check_schema()

    def _check_schema(self):
        logger.info('Setting Data Logger');
        c = self.conn.cursor()
        c.execute(sensor_schema)
        self.conn.commit()
        logger.info('Data Logger ready');

    def log_sensors(self, sensors):
        c = self.conn.cursor()
        for name, data in sensors:
            temp = data['temp']
            if temp is None:
                temp = -1
            c.execute("INSERT INTO sensor_data (sensor_name, temp, status) VALUES ('{}', {}, '{}')".\
                    format(name, temp, data['status']))
        self.conn.commit()


