import unittest
import time
from unittest.mock import patch, MagicMock

from state_machine.state_context import StateContext, DEFAULT_ACCUMULATORS
from state_machine.common_states import SensorError
from state_machine.pit_states import PitInitial, ComingToTemp, OverTemp
from peripherals.temperature_sensors import Max31850Sensors


class TestInitialState(unittest.TestCase):

    @patch('peripherals.temperature_sensors.Max31850Sensors')
    def setUp(self, Sensors):
        self.Sensors = Sensors
        self.sensor_name = 'pit'
        self.user_config = {'pit': {'setPoint': 100}}
        DEFAULT_ACCUMULATORS['pit'].reset()

    def test_no_data(self):
        """ Sensors return no data"""
        sensors = self.Sensors()
        ctx = StateContext(0, self.user_config, sensors)
        s = PitInitial()
        next_state = s.run(self.sensor_name, ctx)

        # In this case no sensor data, we stay in the initial state
        self.assertNotEqual(next_state, s)
        self.assertEqual(next_state.__class__, SensorError)

    def test_sensor_error(self):
        """ Sensor is bad  """
        sensors = self.Sensors.return_value
        sensors.sensor_temp.return_value = {'status': Max31850Sensors.Status.OPEN_CIRCUIT}

        ctx = StateContext(0, self.user_config, sensors)
        s = PitInitial()
        next_state = s.run(self.sensor_name, ctx)

        self.assertNotEqual(next_state, s)
        self.assertEqual(next_state.__class__, SensorError)
        self.assertEqual(next_state.error, Max31850Sensors.Status.OPEN_CIRCUIT)

    def test_setpoint_under(self):
        """ Sensor value is under setpoint """
        sensors = self.Sensors.return_value
        sensors.sensor_temp.return_value = {'status': Max31850Sensors.Status.OK, 'temp': 75}

        ctx = StateContext(0, self.user_config, sensors)
        s = PitInitial()
        next_state = s.run(self.sensor_name, ctx)

        # haven't got enough samples yet
        self.assertEqual(next_state, s)

        t = time.time()
        for i in range(70):
            temp = 75 + i/100.0
            sensors.sensor_temp.return_value = {'status': Max31850Sensors.Status.OK, 'temp': temp}
            ctx = StateContext(t + i, self.user_config, sensors)
            DEFAULT_ACCUMULATORS['pit'].add(t+i, temp)
            next_state = s.run(self.sensor_name, ctx)

        # make it take enough samples
        self.assertEqual(next_state.__class__, ComingToTemp)

    def test_setpoint_over(self):
        """ Sensor value is over or equal setpoint """
        sensors = self.Sensors.return_value
        temp_over = 100 * 1.06
        sensors.sensor_temp.return_value = {'status': Max31850Sensors.Status.OK, 'temp': temp_over}

        ctx = StateContext(0, self.user_config, sensors)
        s = PitInitial()
        t = time.time()
        for i in range(70):
            sensors.sensor_temp.return_value = {'status': Max31850Sensors.Status.OK, 'temp': temp_over}
            ctx = StateContext(t + i, self.user_config, sensors)
            DEFAULT_ACCUMULATORS['pit'].add(t+i, temp_over)
            next_state = s.run(self.sensor_name, ctx)

        self.assertEqual(next_state.__class__, OverTemp)

