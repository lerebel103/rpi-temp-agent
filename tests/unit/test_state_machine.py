import unittest
import time
from unittest.mock import patch, MagicMock

from state_machine import SETPOINT_TIME_THRESHOLD, ALARM_RESET_THRESHOLD, SetPointInitial, StateContext, SensorError, SetPointUnder, SetPointOver, SetPointOverAlarm
from peripherals.temperature_sensors import Max31850Sensors


class TestInitialState(unittest.TestCase):
    
    @patch('peripherals.temperature_sensors.Max31850Sensors')
    def setUp(self, Sensors):
        self.Sensors = Sensors
        self.sensor_name = 'probe1'
        self.state_config = {'probe1': {'setPoint': 100} }

    def test_no_data(self):
        """ Sensors return no data"""
        sensors = self.Sensors()
        ctx = StateContext(0, self.state_config, sensors)
        s = SetPointInitial()
        next_state = s.run(self.sensor_name, ctx)

        # In this case no sensor data, we stay in the initial state
        self.assertNotEqual(next_state, s)
        self.assertEqual(next_state.__class__, SensorError)

    def test_sensor_error(self):
        """ Sensor is bad  """
        sensors = self.Sensors.return_value
        sensors.sensor_temp.return_value = {'status': Max31850Sensors.Status.OPEN_CIRCUIT}

        ctx = StateContext(0, self.state_config, sensors)
        s = SetPointInitial()
        next_state = s.run(self.sensor_name, ctx)

        self.assertNotEqual(next_state, s)
        self.assertEqual(next_state.__class__, SensorError)
        self.assertEqual(next_state.error, Max31850Sensors.Status.OPEN_CIRCUIT)

    def test_setpoint_under(self):
        """ Sensor value is under setpoint """
        sensors = self.Sensors.return_value
        sensors.sensor_temp.return_value = {'status': Max31850Sensors.Status.OK, 'temp': 99.9}

        ctx = StateContext(0, self.state_config, sensors)
        s = SetPointInitial()
        next_state = s.run(self.sensor_name, ctx)

        self.assertNotEqual(next_state, s)
        self.assertEqual(next_state.__class__, SetPointUnder)

    def test_setpoint_over(self):
        """ Sensor value is over or equal setpoint """
        sensors = self.Sensors.return_value
        sensors.sensor_temp.return_value = {'status': Max31850Sensors.Status.OK, 'temp': 100}

        ctx = StateContext(0, self.state_config, sensors)
        s = SetPointInitial()
        next_state = s.run(self.sensor_name, ctx)

        self.assertNotEqual(next_state, s)
        self.assertEqual(next_state.__class__, SetPointOver)


class TestSensorOver(unittest.TestCase):
    
    @patch('peripherals.temperature_sensors.Max31850Sensors')
    def setUp(self, Sensors):
        self.Sensors = Sensors
        self.sensor_name = 'probe1'
        self.state_config = {'probe1': {'setPoint': 100} }

    def test_to_alarm(self):
        """ Alarm state is reached after time in state """
        sensors = self.Sensors.return_value
        sensors.sensor_temp.return_value = {'status': Max31850Sensors.Status.OK, 'temp': 100}


        elapsed = 0
        t = time.time()
        s = SetPointOver(t)
        while elapsed < SETPOINT_TIME_THRESHOLD:
            ctx = StateContext(t + elapsed, self.state_config, sensors)
            next_state = s.run(self.sensor_name, ctx)

            self.assertEqual(next_state, s)
            elapsed += 0.1

        # And now we transition
        ctx = StateContext(t + elapsed, self.state_config, sensors)
        next_state = s.run(self.sensor_name, ctx)
        self.assertNotEqual(next_state, s)
        self.assertEqual(next_state.__class__, SetPointOverAlarm)
       

    def test_to_under(self):
        """ We've been over, but not quite for alarm, back to under """
        sensors = self.Sensors.return_value
        sensors.sensor_temp.return_value = {'status': Max31850Sensors.Status.OK, 'temp': 100}

        elapsed = 0
        t = time.time()
        s = SetPointOver(t)
        while elapsed < SETPOINT_TIME_THRESHOLD/2:
            ctx = StateContext(t + elapsed, self.state_config, sensors)
            next_state = s.run(self.sensor_name, ctx)

            self.assertEqual(next_state, s)
            elapsed += 0.1

        # Now we go under
        sensors.sensor_temp.return_value = {'status': Max31850Sensors.Status.OK, 'temp': 99.9}
        ctx = StateContext(t + elapsed, self.state_config, sensors)
        next_state = s.run(self.sensor_name, ctx)
        self.assertNotEqual(next_state, s)
        self.assertEqual(next_state.__class__, SetPointUnder)

 
class TestSensorUnder(unittest.TestCase):
    
    @patch('peripherals.temperature_sensors.Max31850Sensors')
    def setUp(self, Sensors):
        self.Sensors = Sensors
        self.sensor_name = 'probe1'
        self.state_config = {'probe1': {'setPoint': 100} }

    def test_under(self):
        """ temp consistently under setpoint """
        sensors = self.Sensors.return_value
        sensors.sensor_temp.return_value = {'status': Max31850Sensors.Status.OK, 'temp': 99}

        t = time.time()
        s = SetPointUnder(t)
        elapsed = 0
        while elapsed < 20:
            ctx = StateContext(t + elapsed, self.state_config, sensors)
            next_state = s.run(self.sensor_name, ctx)

            self.assertEqual(next_state, s)
            elapsed += 0.1

    def test_to_over(self):
        """ temp crosses over setpoint """
        sensors = self.Sensors.return_value
        sensors.sensor_temp.return_value = {'status': Max31850Sensors.Status.OK, 'temp': 99}

        t = time.time()
        s = SetPointUnder(t)
        elapsed = 0
        while elapsed < 20:
            ctx = StateContext(t + elapsed, self.state_config, sensors)
            next_state = s.run(self.sensor_name, ctx)

            self.assertEqual(next_state, s)
            elapsed += 0.1

        sensors.sensor_temp.return_value = {'status': Max31850Sensors.Status.OK, 'temp': 100}
        ctx = StateContext(t + elapsed, self.state_config, sensors)
        next_state = s.run(self.sensor_name, ctx)
        self.assertNotEqual(next_state, s)
        self.assertEqual(next_state.__class__, SetPointOver)


class TestSensorOverAlarm(unittest.TestCase):
    
    @patch('peripherals.temperature_sensors.Max31850Sensors')
    def setUp(self, Sensors):
        self.Sensors = Sensors
        self.sensor_name = 'probe1'
        self.state_config = {'probe1': {'setPoint': 100} }

    def test_alarm_sent_once(self):
        """ temp consistently under setpoint """
        sensors = self.Sensors.return_value
        sensors.sensor_temp.return_value = {'status': Max31850Sensors.Status.OK, 'temp': 101}

        t = time.time()
        s = SetPointOverAlarm(t)
        s.send_alarm = MagicMock(name='send_alarm')
        ctx = StateContext(t, self.state_config, sensors)
        ctx = StateContext(t+1, self.state_config, sensors)
        ctx = StateContext(t+2, self.state_config, sensors)
        next_state = s.run(self.sensor_name, ctx)
        self.assertEqual(next_state, s)
        self.assertEqual(1, s.send_alarm.call_count)

    def test_alarm_reset(self):
        """ temp consistently under setpoint """
        sensors = self.Sensors.return_value
        sensors.sensor_temp.return_value = {'status': Max31850Sensors.Status.OK, 'temp': 101}

        t = time.time()
        s = SetPointOverAlarm(t)
        s.send_alarm = MagicMock(name='send_alarm')
        ctx = StateContext(t, self.state_config, sensors)
        next_state = s.run(self.sensor_name, ctx)
        self.assertEqual(next_state, s)

        # Good, now we let temp drop, alarm resets after timeout 
        sensors.sensor_temp.return_value = {'status': Max31850Sensors.Status.OK, 'temp': 99}
        elapsed = 0
        while elapsed < ALARM_RESET_THRESHOLD:
            ctx = StateContext(t + elapsed, self.state_config, sensors)
            next_state = s.run(self.sensor_name, ctx)

            self.assertEqual(next_state, s)
            elapsed += 0.1

        # Next one ticks it over to reset
        elapsed += 0.1
        ctx = StateContext(t + elapsed, self.state_config, sensors)
        next_state = s.run(self.sensor_name, ctx)
        self.assertNotEqual(next_state, s)
        self.assertEqual(next_state.__class__, SetPointUnder)

