"""
Copyright (C) 2021  Augusto Fraga Giachero <augusto.fraga@cnpem.br>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

@license GPL-3.0+ <http://spdx.org/licenses/GPL-3.0+>
"""

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
