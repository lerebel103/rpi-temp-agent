import unittest
import os
from unittest.mock import patch, MagicMock

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
