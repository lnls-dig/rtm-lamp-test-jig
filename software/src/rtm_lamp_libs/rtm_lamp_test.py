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

import sys
import errno
import time
import json
import logging
import yaml
import datetime
import copy
from pathlib import Path
from frugy.fru import Fru
from rtm_lamp_libs import *

class RTMLoggerFile(logging.Handler):
    def __init__(self, logfile, level=logging.NOTSET):
        self.setLevel(level)
        self._logfile = open(logfile, "w")

    def handle(self, record):
        self._logfile.write(record.msg + "\n")

class RTMLoggerTerm(logging.Handler):
    def handle(self, record):
        print(record.msg)

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
                raise RuntimeError("Falha na comunicação com IC14 (I2C ack fail, addr = 0x33)")
            else:
                raise e

    def get_voltages(self):
        try:
            samples = self._max11609.read(7)
        except OSError as e:
            if e.errno == errno.ENXIO:
                raise RuntimeError("Falha na comunicação com IC14 (I2C ack fail, addr = 0x33)")
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
                raise RuntimeError("Falha na comunicação com IC1 (I2C ack fail, addr = 0x20)")
            else:
                raise e
        try:
            self._pca_pwr.set_port_dir(0xE0)
            self._pca_pwr.write_port(0x04)
        except OSError as e:
            if e.errno == errno.ENXIO:
                raise RuntimeError("Falha na comunicação com IC13 (I2C ack fail, addr = 0x21)")
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
                raise RuntimeError("Falha na comunicação com IC1 (I2C ack fail, addr = 0x20)")
            else:
                raise e

    def get_hswap_handle(self):
        try:
            port = self._pca_leds.read_port()
        except OSError as e:
            if e.errno == errno.ENXIO:
                raise RuntimeError("Falha na comunicação com IC1 (I2C ack fail, addr = 0x20)")
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
                raise RuntimeError("Falha na comunicação com IC13 (I2C ack fail, addr = 0x21)")
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
                raise RuntimeError("Falha na comunicação com IC44 (I2C ack fail, addr = 0x4B)")
            else:
                raise e
        try:
            temp_airin = self._temp_airin.get_temp()
        except OSError as e:
            if e.errno == errno.ENXIO:
                raise RuntimeError("Falha na comunicação com IC2 (I2C ack fail, addr = 0x48)")
            else:
                raise e
        try:
            temp_airout = self._temp_airout.get_temp()
        except OSError as e:
            if e.errno == errno.ENXIO:
                raise RuntimeError("Falha na comunicação com IC3 (I2C ack fail, addr = 0x49)")
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
    def __init__(self, devices, log, frufile):
        self._devices = devices
        self._log = log
        self._frufile = frufile

    def run(self):
        passed = False
        try:
            self._run()
            passed = True
        except Exception as e:
            self._log.error(e.__str__())
        return passed

class CheckFRU(Test):
    def _run(self):
        self._log.info("Checando eeprom")
        fru_bin = self._devices.eeprom.read(0x0000, 2048)
        fru = Fru()
        try:
            fru.deserialize(fru_bin)
        except RuntimeError as e:
            return
        self._log.debug(fru.dump_yaml())
        self._log.info("FRU já programada, deseja continuar mesmo assim [s/n]?")
        ans = input()
        self._log.debug(ans)
        if ans != "s" and ans != "S":
            raise RuntimeError("FRU já programada")

class TestLED(Test):
    def _run(self):
        self._log.info("Testando LEDs")
        self._devices.gpio.set_leds(True, True, True)
        self._log.info("LEDs Azul (LED1), Verde (LED2) e Vermelho (LED3) acesos [s/n]?")
        ans = input()
        self._log.debug(ans)
        if ans != "s" and ans != "S":
            raise RuntimeError("Falha nos LEDs")
        self._devices.gpio.set_leds(False, False, False)
        self._log.info("LEDs Azul (LED1), Verde (LED2) e Vermelho (LED3) apagados [s/n]?")
        ans = input()
        self._log.debug(ans)
        if ans != "s" and ans != "S":
            raise RuntimeError("Falha nos LEDs")

class TestTemps(Test):
    def _run(self):
        self._log.info("Testando sensores de temperatura")
        temps = self._devices.tmeas.get_temps()
        for key, val in temps.items():
            if val < 10 or val > 40:
                raise RuntimeError("Temperatura fora  da faixa especificada: {} = {:.02f}°C".format(key, val))
            else:
                self._log.info("Temperatura {} = {:.02f}°C OK".format(key, val))

class TestSupply(Test):
    def test_voltages(self, expected_voltages, maximum_voltages, timeout):
        """Test power supply voltages"""
        while timeout > 0:
            vmeas = self._devices.vmeas.get_voltages()
            ok = True
            for key, val in vmeas.items():
                if abs(val) > abs(maximum_voltages[key]):
                    greater_lesser = ">" if val > maximum_voltages[key] else "<"
                    raise RuntimeError("  Alimentação {} = {:.02f}V {} {:.02f}V (sobretensão) FALHOU".format(key, val, greater_lesser, maximum_voltages[key]))
                err = val - expected_voltages[key][0]
                if abs(err) >= expected_voltages[key][1]:
                    ok = False
            if ok:
                break
            else:
                timeout = timeout - 1
            time.sleep(1)
        vmeas = self._devices.vmeas.get_voltages()
        for key, val in vmeas.items():
            err = val - expected_voltages[key][0]
            if abs(err) < expected_voltages[key][1]:
                self._log.info("  Alimentação {} = {:.02f}V OK".format(key, val))
            else:
                raise RuntimeError("  Alimentação {} = {:.02f}V FALHOU".format(key, val))

    def _run(self):
        self._log.info("Testando alimentação")
        max_abs_voltages = {"VS1" : 5.1,
                            "VS2" : 5.1,
                            "-7V" : -7.5,
                            "+7V" : 7.5,
                            "+5V" : 5.5,
                            "+3V3" : 3.5,
                            "+2V5" : 2.6}
        try:
            self._devices.gpio.set_pwr(en_vs1=False, en_vs2=False, en_7v=False, en_5v=False)
            self._log.info("Desligando alimentações...")
            expected_voltages = {"VS1" : [0, 0.1],
                                 "VS2" : [0, 0.1],
                                 "-7V" : [0, 0.2],
                                 "+7V" : [0, 0.2],
                                 "+5V" : [0, 0.15],
                                 "+3V3" : [0, 0.1],
                                 "+2V5" : [0, 0.1]}
            self.test_voltages(expected_voltages, max_abs_voltages, 20)
            self._devices.gpio.set_pwr(en_vs1=False, en_vs2=False, en_7v=True, en_5v=True)
            self._log.info("Habilitando +7V, -7V e +5V...")
            expected_voltages = {"VS1" : [0, 0.1],
                                 "VS2" : [0, 0.1],
                                 "-7V" : [-7, 0.2],
                                 "+7V" : [7, 0.2],
                                 "+5V" : [5, 0.15],
                                 "+3V3" : [3.3, 0.1],
                                 "+2V5" : [2.5, 0.1]}
            self.test_voltages(expected_voltages, max_abs_voltages, 20)
            self._devices.gpio.set_pwr(en_vs1=True, en_vs2=False, en_7v=False, en_5v=False)
            self._log.info("Habilitando VS1...")
            expected_voltages = {"VS1" : [4, 0.1],
                                 "VS2" : [0, 0.1],
                                 "-7V" : [0, 0.2],
                                 "+7V" : [0, 0.2],
                                 "+5V" : [0, 0.15],
                                 "+3V3" : [0, 0.2],
                                 "+2V5" : [0, 0.2]}
            self.test_voltages(expected_voltages, max_abs_voltages, 20)
            self._devices.gpio.set_pwr(en_vs1=False, en_vs2=True, en_7v=False, en_5v=False)
            self._log.info("Habilitando VS2...")
            expected_voltages = {"VS1" : [0, 0.1],
                                 "VS2" : [4, 0.1],
                                 "-7V" : [0, 0.2],
                                 "+7V" : [0, 0.2],
                                 "+5V" : [0, 0.15],
                                 "+3V3" : [0, 0.2],
                                 "+2V5" : [0, 0.2]}
            self.test_voltages(expected_voltages, max_abs_voltages, 20)
            self._devices.gpio.set_pwr(en_vs1=True, en_vs2=True, en_7v=True, en_5v=True)
            self._log.info("Habilitando VS1, VS2, -7V, +7V e +5V...")
            expected_voltages = {"VS1" : [4, 0.1],
                                 "VS2" : [4, 0.1],
                                 "-7V" : [-7, 0.2],
                                 "+7V" : [7, 0.2],
                                 "+5V" : [5, 0.15],
                                 "+3V3" : [3.3, 0.2],
                                 "+2V5" : [2.5, 0.2]}
            self.test_voltages(expected_voltages, max_abs_voltages, 20)
        except RuntimeError as e:
            self._log.info("Desligando alimentações...")
            self._devices.gpio.set_pwr(en_vs1=False, en_vs2=False, en_7v=False, en_5v=False)
            raise e
        self._log.info("Desligando alimentações...")
        self._devices.gpio.set_pwr(en_vs1=False, en_vs2=False, en_7v=False, en_5v=False)

class ConfigureCDCE906(Test):
    def _run(self):
        self._log.info("Configurando CDCE906...")
        cfg = {
            "clk_src": "CLK_SRC_CLKIN_DIFF",
            "pll_div_m": [
                1,
                27,
                375
            ],
            "pll_div_n": [
                8,
                250,
                3136
            ],
            "pll_vco_mux": [
                "PLL_VCO_MUX_PLL",
                "PLL_VCO_MUX_PLL",
                "PLL_VCO_MUX_PLL"
            ],
            "pll_fvco": [
                "PLL_FVCO_180_300MHZ",
                "PLL_FVCO_180_300MHZ",
                "PLL_FVCO_180_300MHZ"
            ],
            "ssc_mod_amount": "SSC_MOD_AMOUNT_OFF",
            "ssc_mod_freq": "SSC_MOD_FREQ_3286",
            "s0_cfg": "S0_CFG_POWER_DOWN_CTRL",
            "s1_cfg": "S1_CFG_Yx_FIXED_OUTPUT_CTRL",
            "pll_sel": [
                "Px_PLL_SEL_BYPASS",
                "Px_PLL_SEL_BYPASS",
                "Px_PLL_SEL_BYPASS",
                "Px_PLL_SEL_BYPASS",
                "Px_PLL_SEL_PLL1",
                "Px_PLL_SEL_PLL1"
            ],
            "p_div": [
                1,
                120,
                30,
                60,
                32,
                4
            ],
            "y_slew": [
                "Yx_SLEW_CFG_NOMINAL_1NS",
                "Yx_SLEW_CFG_NOMINAL_1NS",
                "Yx_SLEW_CFG_NOMINAL_1NS",
                "Yx_SLEW_CFG_NOMINAL_1NS",
                "Yx_SLEW_CFG_NOMINAL_1NS",
                "Yx_SLEW_CFG_NOMINAL_1NS"
            ],
            "y_p_sel": [
                "Yx_Px_SEL_P0",
                "Yx_Px_SEL_P1",
                "Yx_Px_SEL_P2",
                "Yx_Px_SEL_P3",
                "Yx_Px_SEL_P2",
                "Yx_Px_SEL_P2"
            ],
            "y_out": [
                "Yx_OUT_CFG_EN",
                "Yx_OUT_CFG_DIS_HIGH",
                "Yx_OUT_CFG_DIS_LOW",
                "Yx_OUT_CFG_DIS_LOW",
                "Yx_OUT_CFG_DIS_LOW",
                "Yx_OUT_CFG_DIS_LOW"
            ]
        }
        self._log.debug("Configuração enviada:")
        self._log.debug(json.dumps(cfg, indent=4))
        self._devices.cdce906.set_cfg(cfg, write_eeprom=True)
        time.sleep(.2)
        self._log.debug("Configuração lida:")
        cfg_read = self._devices.cdce906.get_cfg()
        self._log.debug(json.dumps(cfg_read, indent=4))
        if cfg != cfg_read:
            raise RuntimeError("Configuração inválida do CDCE906 (IC12)")

class ProgramFRU(Test):
    def _run(self):
        self._log.info("Programando eeprom")
        with open(self._frufile, "r") as fru_file:
            fru_yaml_data = fru_file.read()
            fru_dict = yaml.safe_load(fru_yaml_data)
            self._log.debug("Template YAML para FRU:")
            self._log.debug(fru_yaml_data)

        datenow = datetime.datetime.now()
        serial_file = open(str(Path.home()) + "/.rtm_lamp_serial", "r+")
        try:
            serialnum = int(serial_file.readline())
        except ValueError as e:
            serialnum = 1

        serialnum_str = "CN{:05d}".format(serialnum)
        self._log.info("Serial number: {}".format(serialnum_str))
        fru_dict["BoardInfo"]["mfg_date_time"] = datetime.datetime(datenow.year,
                                                                   datenow.month,
                                                                   datenow.day,
                                                                   datenow.hour,
                                                                   datenow.minute)
        fru_dict["BoardInfo"]["serial_number"] = serialnum_str
        fru_dict["ProductInfo"]["serial_number"] = serialnum_str
        fru_dict["ProductInfo"]["asset_tag"] = serialnum_str

        fru = Fru(copy.deepcopy(fru_dict)) # frugy modifies the
                                           # dictionary, so you should
                                           # pass a copy if you want
                                           # to access the dictionary
                                           # again.
        self._devices.eeprom.write(0x0000, fru.serialize())
        time.sleep(0.5)
        self._log.info("Lendo eeprom")
        fru.deserialize(self._devices.eeprom.read(0x0000, 2048))
        if fru.to_dict() != fru_dict:
            self._log.debug("Dicionário gerado:")
            self._log.debug(str(fru_dict))
            self._log.debug("Dicionário lido:")
            self._log.debug(str(fru.to_dict()))
            raise RuntimeError("Conteúdo FRU da eeprom difere do programado")
        serialnum = serialnum + 1
        serial_file.seek(0)
        serial_file.write(str(serialnum) + "\n")
        serial_file.close()

def main():
    try:
        i2c_bus = int(sys.argv[1])
        frufile = sys.argv[2]
        logfile = sys.argv[3]
    except:
        print("Usage: {} i2c_bus fru-file.yml logfile".format(sys.argv[0]))
        exit(1)

    log = logging.Logger("rtm-test-logger")
    log.addHandler(RTMLoggerFile(logfile, logging.DEBUG))
    log.addHandler(RTMLoggerTerm(logging.INFO))

    log.info("Início do procedimento de testes")
    try:
        devices = RTMDevices(i2c_bus)
    except Exception as e:
        log.error(e.__str__)
        exit(1)
    log.info("Dispositivos I2C inicializados")
    log.info("------------------------------")

    tests = [
        CheckFRU(devices, log, frufile),
        TestLED(devices, log, frufile),
        TestTemps(devices, log, frufile),
        TestSupply(devices, log, frufile),
        ConfigureCDCE906(devices, log, frufile),
        ProgramFRU(devices, log, frufile),
    ]

    for tnum, test in enumerate(tests):
        if test.run():
            log.info("Teste {:d}/{:d} OK".format(tnum + 1, len(tests)))
        else:
            log.error("Teste {:d}/{:d} FALHOU".format(tnum + 1, len(tests)))
            exit(1)
        log.info("------------------------------")

if __name__ == "__main__":
    main()
