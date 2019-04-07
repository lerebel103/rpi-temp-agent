import unittest
import time
from unittest.mock import patch, MagicMock

from state_machine.state_context import StateContext, DEFAULT_ACCUMULATORS
from state_machine.common_states import SensorError
from state_machine.pit_states import PitInitial, ComingToTemp, OverTemp, LidOpen, FlameOut, UpToTemp, \
    SETPOINT_ERROR_PERC
from peripherals.temperature_sensors import Max31850Sensors


class TestInitialState(unittest.TestCase):

    @patch('peripherals.temperature_sensors.Max31850Sensors')
    def setUp(self, Sensors):
        self.Sensors = Sensors
        self.sensor_name = 'pit'
        self.user_config = {'pit': {'setPoint': 100}}

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
            next_state = s.run(self.sensor_name, ctx)

        self.assertEqual(next_state.__class__, OverTemp)


class TestComingToTemp(unittest.TestCase):

    @patch('peripherals.temperature_sensors.Max31850Sensors')
    def setUp(self, Sensors):
        self.Sensors = Sensors
        self.sensor_name = 'pit'
        self.user_config = {'pit': {'setPoint': 100}}

    def test_lid_open(self):
        """ detects lid open condition """
        sensors = self.Sensors()
        s = ComingToTemp()

        last_temp, last_time, previous_state = self.fill_temp_up(s, sensors)

        # create condition, inject 5s of decay
        last_temp2 = None
        for i in range(3):
            temp = last_temp - i/3
            last_temp2 = temp
            sensors.sensor_temp.return_value = {'status': Max31850Sensors.Status.OK, 'temp': temp}
            ctx = StateContext(last_time + i, self.user_config, sensors)
            next_state = s.run(self.sensor_name, ctx)
            self.assertEqual(next_state, previous_state)
            previous_state = next_state

        # Next one triggers it
        sensors.sensor_temp.return_value = {'status': Max31850Sensors.Status.OK, 'temp': last_temp2 - 1}
        ctx = StateContext(last_time + i + 1, self.user_config, sensors)
        next_state = s.run(self.sensor_name, ctx)
        self.assertNotEqual(next_state, previous_state)
        self.assertNotEqual(next_state.__class__, LidOpen.__class__)

    def fill_temp_up(self, s, sensors):
        # steady temp climb
        t = time.time()
        previous_state = s
        last_time = None
        last_temp = None
        for i in range(70):
            last_temp = 75 + i / 10.0
            last_time = t + i
            sensors.sensor_temp.return_value = {'status': Max31850Sensors.Status.OK, 'temp': last_temp}
            ctx = StateContext(last_time, self.user_config, sensors)
            next_state = s.run(self.sensor_name, ctx)
            self.assertEqual(next_state, previous_state)
            previous_state = next_state
        return last_temp, last_time, previous_state

    def test_flame_out(self):
        """ detects flame out condition """
        sensors = self.Sensors()
        s = ComingToTemp()

        # Fill up
        last_temp, last_time, previous_state = self.fill_temp_up(s, sensors)

        # now we go down
        for i in range(5*60):
            sensors.sensor_temp.return_value = {'status': Max31850Sensors.Status.OK, 'temp': last_temp - last_temp * 0.001 * i }
            ctx = StateContext(last_time+i, self.user_config, sensors)
            next_state = s.run(self.sensor_name, ctx)

            if next_state != previous_state:
                break

        self.assertEqual(FlameOut, next_state.__class__)
        self.assertEqual(85, i)

    def test_up_to_temp(self):
        """ We're ok, in band of setpoint """
        sensors = self.Sensors()

        # middle
        sensors.sensor_temp.return_value = {'status': Max31850Sensors.Status.OK,
                                            'temp': 100}
        ctx = StateContext(0, self.user_config, sensors)
        s = ComingToTemp()
        next_state = s.run(self.sensor_name, ctx)

        self.assertEqual(UpToTemp, next_state.__class__)

        # Low boundary
        sensors.sensor_temp.return_value = {'status': Max31850Sensors.Status.OK,
                                            'temp': 100 - 100*SETPOINT_ERROR_PERC}
        ctx = StateContext(0, self.user_config, sensors)
        s = ComingToTemp()
        next_state = s.run(self.sensor_name, ctx)

        self.assertEqual(UpToTemp, next_state.__class__)

        # Up boundary
        sensors.sensor_temp.return_value = {'status': Max31850Sensors.Status.OK,
                                            'temp': 100 + 100*SETPOINT_ERROR_PERC}
        s = ComingToTemp()
        ctx = StateContext(0, self.user_config, sensors)
        next_state = s.run(self.sensor_name, ctx)

        # Off boundary (Down)
        sensors.sensor_temp.return_value = {'status': Max31850Sensors.Status.OK,
                                            'temp': 100 - 100*SETPOINT_ERROR_PERC - 0.1}
        ctx = StateContext(0, self.user_config, sensors)
        s = ComingToTemp()
        next_state = s.run(self.sensor_name, ctx)

        self.assertEqual(FlameOut, next_state.__class__)
