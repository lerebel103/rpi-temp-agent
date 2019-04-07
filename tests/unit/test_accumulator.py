import unittest
import time

from accumulator import Accumulator


class TestAccumulator(unittest.TestCase):

    def test_max_interval(self):
        """ Make sure internal queue keeps just as many items as we need """
        acc = Accumulator(50)

        for k in range(10):
            t = time.time()

            for delta in range(100):
                acc.add(t + delta, delta)

            self.assertEqual(51, acc.length())
            self.assertEqual(50, acc.interval())

            # go over again and we get the same result
            acc.reset()
    
    def test_derivative_all(self):
        """ Make sure derivative is what we expect on sample set """
        acc = Accumulator(50)

        t = time.time()
        for delta in range(100):
            acc.add(t + delta, delta)

        # Then we have 1 here
        self.assertAlmostEqual(1, acc.linear_derivative(), 1)

        acc.reset()

        # reverse
        for delta in range(100):
            acc.add(t + delta, 100 - delta)

        # Then we have 1 here
        self.assertAlmostEqual(-1, acc.linear_derivative(), 1)

    def test_derivative_delta_back(self):
        """ get derivative from a specific point back """
        acc = Accumulator(100)

        # zero points
        self.assertAlmostEqual(0, acc.linear_derivative(), 1)

        t = time.time()
        for delta in range(50):
            acc.add(t + delta, delta)

        # Then we have 1 here
        self.assertAlmostEqual(1, acc.linear_derivative(), 1)

        # reverse
        for delta in range(50, 100):
            acc.add(t + delta, 100 - delta)

        self.assertAlmostEqual(0, acc.linear_derivative(), 1)

        # exactly mid point, we have -1 by definition

        # Then we have 1 here
        self.assertAlmostEqual(-1, acc.linear_derivative(t+50), 1)
        # same forward
        self.assertAlmostEqual(-1, acc.linear_derivative(t+80), 1)

        # on edge?
        self.assertAlmostEqual(0, acc.linear_derivative(t+99), 1)
        self.assertAlmostEqual(0, acc.linear_derivative(t+100), 1)
