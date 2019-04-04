import sys

# This is so we can run tests on any platform without requiring the DS18B20 module on
# actual hardware
sys.modules['DS18B20'] = __import__('tests.mocked.DS18B20')


