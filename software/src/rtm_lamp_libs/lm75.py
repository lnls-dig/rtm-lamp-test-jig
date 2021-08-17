import smbus2

class lm75():
    def __init__(self, bus_number, slave_addr):
        self._bus = smbus2.SMBus(bus_number)
        self._slave_addr = slave_addr

    def get_temp(self):
        data = self._bus.read_i2c_block_data(self._slave_addr, 0x00, 2)
        temp_int = int(data[0] * 256 + data[1])
        if temp_int >= 0x8000:
            temp_int = temp_int - 0x10000
        return temp_int / 256.0
