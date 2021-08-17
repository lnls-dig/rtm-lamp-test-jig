import time
import smbus2

class ee24xx64():
    def __init__(self, bus_number, slave_addr):
        self._bus = smbus2.SMBus(bus_number)
        self._slave_addr = slave_addr
        self._page_size = 32
        self._mem_size = 8192
        self._write_retries = 4

    def read(self, address, length):
        addr = bytes([address >> 8, address & 0xFF])
        addr_msg = smbus2.i2c_msg.write(self._slave_addr, addr)
        data_msg = smbus2.i2c_msg.read(self._slave_addr, length)
        self._bus.i2c_rdwr(addr_msg, data_msg)
        return bytes(data_msg)

    def write(self, address, data):
        msgs = []
        bytes_left = len(data)
        offset = 0
        assert(address + bytes_left <= self._mem_size)
        while True:
            max_len = self._page_size - ((address + offset) % self._page_size)
            if bytes_left <= max_len:
                self._write_page(address + offset, data[offset:offset + bytes_left])
                break
            else:
                self._write_page(address + offset, data[offset:offset + max_len])
                bytes_left = bytes_left - max_len
                offset = offset + max_len

    def _write_page(self, address, data):
        payload = bytes([address >> 8, address & 0xFF]) + data
        msg = smbus2.i2c_msg.write(self._slave_addr, payload)
        for i in range(self._write_retries):
            try:
                self._bus.i2c_rdwr(msg)
                break
            except OSError:
                time.sleep(0.005)
