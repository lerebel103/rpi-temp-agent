from memoized import memoized


@memoized
def get_cpu_id():
    """
    Reads the CPU Id to allow us to uniquely identify this Thing.
    :return: Unique identifier for this hardware.
    """
    cpu_serial = "ERROR000000000"
    with open('/proc/cpuinfo', 'r') as f:
        for line in f:
            if line.startswith('Serial'):
                cpu_serial = line.split(':')[1].strip(' ')
                break
    return cpu_serial
