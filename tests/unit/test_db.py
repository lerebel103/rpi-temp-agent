import unittest
import os

from db.data_logger import DataLogger

test_db = '/tmp/TestDataLogger.sqlite'


class TestDataLogger(unittest.TestCase):

    def setUp(self):
        if os.path.exists(test_db):
            os.remove(test_db)

    def test_add_tokens(self):
        """ added tokens need to come out the same. """
        db = DataLogger(test_db, '1234')
        source = ['1a', '2v', '3r', 'a', 'b']
        db.save_push_tokens(source)

        tokens = db.push_tokens()
        self.assertEqual(source, tokens)

    def test_delete_tokens(self):
        """ added tokens need to come out the same. """
        db = DataLogger(test_db, '1234')
        source = ['1a', '2v', '3r', 'a', 'b']
        db.save_push_tokens(source)

        # delete specific tokens
        to_delete = ['2v', 'a', 'b']
        db.delete_tokens(to_delete)

        tokens = db.push_tokens()
        self.assertEqual(['1a', '3r'], tokens)

    def test_log_sensor(self):
        db = DataLogger(test_db, '1234')

        for i in range(100):
            db.log_sensors(i, [('probe1', {'temp': 100 + i, 'status': 'OK'}),
                               ('probe2', {'temp': 200 + i, 'status': 'OK'}),
                               ('probe3', {'temp': 300 + i, 'status': 'OK'})]
                           )

        # Get them back
        results = db.data_for_sensor('probe1')
        i = 1
        for r in results:
            self.assertTrue('timestamp' in r)
            self.assertEqual(i, r['timestamp'])
            self.assertTrue('temp' in r)
            self.assertEqual(100 + i, r['temp'])
            self.assertTrue('status' in r)
            self.assertEqual('OK', r['status'])
            i += 1

        results = db.data_for_sensor('probe2')
        i = 1
        for r in results:
            self.assertTrue('timestamp' in r)
            self.assertEqual(i, r['timestamp'])
            self.assertTrue('temp' in r)
            self.assertEqual(200 + i, r['temp'])
            self.assertTrue('status' in r)
            self.assertEqual('OK', r['status'])
            i += 1

        results = db.data_for_sensor('probe3')
        i = 1
        for r in results:
            self.assertTrue('timestamp' in r)
            self.assertEqual(i, r['timestamp'])
            self.assertTrue('temp' in r)
            self.assertEqual(300 + i, r['temp'])
            self.assertTrue('status' in r)
            self.assertEqual('OK', r['status'])
            i += 1

    def test_log_sensor_start(self):
        db = DataLogger(test_db, '1234')

        for i in range(100):
            db.log_sensors(i, [('probe1', {'temp': 100 + i, 'status': 'OK'}),
                               ('probe2', {'temp': 200 + i, 'status': 'OK'}),
                               ('probe3', {'temp': 300 + i, 'status': 'OK'})]

                           )

        # with start offset
        for start in range(10, 100, 10):
            results = db.data_for_sensor('probe1', start)
            k = 0
            for r in results:
                self.assertTrue('timestamp' in r)
                self.assertEqual(start + k, r['timestamp'])
                self.assertTrue('temp' in r)
                self.assertEqual(100 + start + k, r['temp'])
                self.assertTrue('status' in r)
                self.assertEqual('OK', r['status'])
                k += 1

    def test_log_sensor_start_end(self):
        db = DataLogger(test_db, '1234')

        for i in range(100):
            db.log_sensors(i, [('probe1', {'temp': 100 + i, 'status': 'OK'}),
                               ('probe2', {'temp': 200 + i, 'status': 'OK'}),
                               ('probe3', {'temp': 300 + i, 'status': 'OK'})]

                           )

        # with start offset
        for start in range(10, 100, 10):
            end = start + 5
            results = db.data_for_sensor('probe1', start, end)
            self.assertEqual(6, len(results))
            k = 0
            for r in results:
                self.assertTrue('timestamp' in r)
                self.assertEqual(start + k, r['timestamp'])
                self.assertTrue('temp' in r)
                self.assertEqual(100 + start + k, r['temp'])
                self.assertTrue('status' in r)
                self.assertEqual('OK', r['status'])
                k += 1
