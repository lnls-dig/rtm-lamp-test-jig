#!/usr/bin/env python3

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

import os
import errno
import time
from rtm_lamp_libs import *

class VoltMeasure():
    def __init__(self, bus):
        self._max11609 = max116xx.max116xx(bus, 0x33)
        max11609_cfg = {
            "ref_sel"     : "REF_INT_ON",
            "clk_sel"     : "CLK_INT",
            "pol_sel"     : "UNIPOLAR",
            "scan_mode"   : "SCAN_FROM_AIN0",
            "diff_mode"   : "SINGLE_ENDED",
            "channel_sel" : 6
        }
        try:
            self._max11609.set_config(max11609_cfg)
        except OSError as e:
            if e.errno == errno.ENXIO:
                raise Exception("Falha na comunicação com IC14 (I2C ack fail, addr = 0x33)")
            else:
                raise e

    def get_voltages(self):
        try:
            samples = self._max11609.read(7)
        except OSError as e:
            if e.errno == errno.ENXIO:
                raise Exception("Falha na comunicação com IC14 (I2C ack fail, addr = 0x33)")
            else:
                raise e
        measurements = {
            "VS1" : 5e-3 * samples[0],
            "VS2" : 5e-3 * samples[1],
            "-7V" : -10e-3 * samples[2],
            "+7V" : 10e-3 * samples[3],
            "+2V5" : 4e-3 * samples[4],
            "+3V3" : 4e-3 * samples[5],
            "+5V" : 8e-3 * samples[6],
        }
        return measurements

class GpioCtrl():
    def __init__(self, bus):
        self._pca_leds = pca9554.pca9554(bus, 0x20)
        self._pca_pwr = pca9554.pca9554(bus, 0x21)
        try:
            self._pca_leds.set_port_dir(0x1F)
            self._pca_leds.write_port(0xE0)
        except OSError as e:
            if e.errno == errno.ENXIO:
                raise Exception("Falha na comunicação com IC1 (I2C ack fail, addr = 0x20)")
            else:
                raise e
        try:
            self._pca_pwr.set_port_dir(0xE0)
            self._pca_pwr.write_port(0x04)
        except OSError as e:
            if e.errno == errno.ENXIO:
                raise Exception("Falha na comunicação com IC13 (I2C ack fail, addr = 0x21)")
            else:
                raise e

    def set_leds(self, l1, l2, hswap):
        port = 0xE0
        if l1:
            port = port & 0xDF
        if l2:
            port = port & 0xBF
        if hswap:
            port = port & 0x7F
        try:
            self._pca_leds.write_port(port)
        except OSError as e:
            if e.errno == errno.ENXIO:
                raise Exception("Falha na comunicação com IC1 (I2C ack fail, addr = 0x20)")
            else:
                raise e

    def get_hswap_handle(self):
        try:
            port = self._pca_leds.read_port()
        except OSError as e:
            if e.errno == errno.ENXIO:
                raise Exception("Falha na comunicação com IC1 (I2C ack fail, addr = 0x20)")
            else:
                raise e
        if port & 0x01:
            return False
        else:
            return True

    def set_pwr(self, en_vs1, en_vs2, en_7v, en_5v):
        port = 0x00
        if en_vs1:
            port = port | 0x01
        if en_vs2:
            port = port | 0x02
        if en_7v:
            port = port | 0x10
        else:
            port = port | 0x04
        if en_5v:
            port = port | 0x08
        try:
            self._pca_pwr.write_port(port)
        except OSError as e:
            if e.errno == errno.ENXIO:
                raise Exception("Falha na comunicação com IC13 (I2C ack fail, addr = 0x21)")
            else:
                raise e

class Temperature():
    def __init__(self, bus):
        self._temp_supply = lm75.lm75(bus, 0x4B)
        self._temp_airin = lm75.lm75(bus, 0x48)
        self._temp_airout = lm75.lm75(bus, 0x49)

    def get_temps(self):
        try:
            temp_supply = self._temp_supply.get_temp()
        except OSError as e:
            if e.errno == errno.ENXIO:
                raise Exception("Falha na comunicação com IC44 (I2C ack fail, addr = 0x4B)")
            else:
                raise e
        try:
            temp_airin = self._temp_airin.get_temp()
        except OSError as e:
            if e.errno == errno.ENXIO:
                raise Exception("Falha na comunicação com IC2 (I2C ack fail, addr = 0x48)")
            else:
                raise e
        try:
            temp_airout = self._temp_airout.get_temp()
        except OSError as e:
            if e.errno == errno.ENXIO:
                raise Exception("Falha na comunicação com IC3 (I2C ack fail, addr = 0x49)")
            else:
                raise e
        temps = {
            "supply" : temp_supply,
            "airin"  : temp_airin,
            "airout" : temp_airout,
        }
        return temps

class RTMDevices():
    def __init__(self, i2c_bus):
        self.gpio = GpioCtrl(i2c_bus)
        self.vmeas = VoltMeasure(i2c_bus)
        self.tmeas = Temperature(i2c_bus)
        self.cdce906 = cdce906.cdce906(i2c_bus, 0x69)
        self.eeprom = ee24xx64.ee24xx64(i2c_bus, 0x50)

class Test():
    def __init__(self, devices):
        self._devices = devices

    def run(self):
        passed = False
        try:
            self._run()
            passed = True
        except Exception as e:
            print(e.__str__())
        return passed

class TestLED(Test):
    def _run(self):
        print("Testando LEDs")
        self._devices.gpio.set_leds(True, True, True)
        print("LEDs Azul (LED1), Verde (LED2) e Vermelho (LED3) acesos [s/n]?")
        ans = input()
        if ans != "s" and ans != "S":
            raise Exception("Falha nos LEDs")
        self._devices.gpio.set_leds(False, False, False)
        print("LEDs Azul (LED1), Verde (LED2) e Vermelho (LED3) apagados [s/n]?")
        ans = input()
        if ans != "s" and ans != "S":
            raise Exception("Falha nos LEDs")

class TestTemps(Test):
    def _run(self):
        print("Testando sensores de temperatura")
        temps = self._devices.tmeas.get_temps()
        for key, val in temps.items():
            if val < 10 or val > 40:
                raise Exception("Temperatura fora  da faixa especificada: {} = {:.02f}°C".format(key, val))
            else:
                print("Temperatura {} = {:.02f}°C OK".format(key, val))

def main():
    i2c_bus = 2
    print("Início do procedimento de testes")
    try:
        devices = RTMDevices(i2c_bus)
    except Exception as e:
        print(e.__str__)
        exit(1)
    print("Dispositivos I2C inicializados")
    print("------------------------------")

    tests = [TestLED(devices), TestTemps(devices)]

    for tnum, test in enumerate(tests):
        if test.run():
            print("Teste {:d}/{:d} OK".format(tnum + 1, len(tests)))
        else:
            print("Teste {:d}/{:d} FALHOU".format(tnum + 1, len(tests)))
            exit(1)
        print("------------------------------")

if __name__ == "__main__":
    main()
