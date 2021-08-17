import smbus2

class pca9554():
    def __init__(self, bus_number, slave_addr):
        self._bus = smbus2.SMBus(bus_number)
        self._slave_addr = slave_addr

    def set_port_dir(self, iodir):
        self._bus.write_byte_data(self._slave_addr, 0x03, iodir)

    def write_port(self, byte):
        self._bus.write_byte_data(self._slave_addr, 0x01, byte)

    def read_port(self):
        return self._bus.read_byte_data(self._slave_addr, 0x00)
