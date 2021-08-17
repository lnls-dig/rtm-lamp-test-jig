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
