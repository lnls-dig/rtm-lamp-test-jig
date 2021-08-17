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
import ctypes
import glob
import os

clk_src = {
    "CLK_SRC_CRYSTAL" : 0,
    "CLK_SRC_CLKIN0_LVCMOS" : 1,
    "CLK_SRC_CLKIN1_LVCMOS" : 2,
    "CLK_SRC_CLKIN_DIFF" : 3,
    "CLK_SRC_INVALID" : 4,
}

clk_src_inv = {val: key for key, val in clk_src.items()}

pll_vco_mux = {
    "PLL_VCO_MUX_PLL" : 0,
    "PLL_VCO_MUX_VCO" : 1,
}

pll_vco_mux_inv = {val: key for key, val in pll_vco_mux.items()}

pll_fvco = {
    "PLL_FVCO_80_200MHZ" : 0,
    "PLL_FVCO_180_300MHZ" : 1,
}

pll_fvco_inv = {val: key for key, val in pll_fvco.items()}

s0_cfg = {
    "S0_CFG_POWER_DOWN_CTRL" : 0,
    "S0_CFG_PLL_DIV_BYPASS_CTRL" : 1,
    "S0_CFG_CLKSEL_CTRL" : 2,
    "S0_CFG_I2C_ADDR" : 3,
}

s0_cfg_inv = {val: key for key, val in s0_cfg.items()}

s1_cfg = {
    "S1_CFG_Yx_FIXED_OUTPUT_CTRL" : 0,
    "S1_CFG_Yx_TRISTATE_CTRL" : 1,
    "S1_CFG_I2C_ADDR" : 2,
    "S1_CFG_INVALID" : 3,
}

s1_cfg_inv = {val: key for key, val in s1_cfg.items()}

px_pll_sel = {
    "Px_PLL_SEL_BYPASS" : 0,
    "Px_PLL_SEL_PLL1" : 1,
    "Px_PLL_SEL_PLL2" : 2,
    "Px_PLL_SEL_PLL2_SSC" : 3,
    "Px_PLL_SEL_PLL3" : 4,
    "Px_PLL_SEL_INVALID" : 5,
}

px_pll_sel_inv = {val: key for key, val in px_pll_sel.items()}

yx_out_cfg = {
    "Yx_OUT_CFG_EN" : 0,
    "Yx_OUT_CFG_EN_INV" : 1,
    "Yx_OUT_CFG_DIS_LOW" : 2,
    "Yx_OUT_CFG_DIS_HIGH" : 3,
}

yx_out_cfg_inv = {val: key for key, val in yx_out_cfg.items()}

yx_slew_cfg = {
    "Yx_SLEW_CFG_NOMINAL" : 0,
    "Yx_SLEW_CFG_NOMINAL_1NS" : 1,
    "Yx_SLEW_CFG_NOMINAL_2NS" : 2,
    "Yx_SLEW_CFG_NOMINAL_3NS" : 3,
}

yx_slew_cfg_inv = {val: key for key, val in yx_slew_cfg.items()}

yx_px_sel = {
    "Yx_Px_SEL_P0" : 0,
    "Yx_Px_SEL_P1" : 1,
    "Yx_Px_SEL_P2" : 2,
    "Yx_Px_SEL_P3" : 3,
    "Yx_Px_SEL_P4" : 4,
    "Yx_Px_SEL_P5" : 5,
    "Yx_Px_SEL_INVALID" : 6,
}

yx_px_sel_inv = {val: key for key, val in yx_px_sel.items()}

ssc_mod_amount = {
    "SSC_MOD_AMOUNT_OFF" : 0,
    "SSC_MOD_AMOUNT_0P1_CENTER" : 1,
    "SSC_MOD_AMOUNT_0P25_CENTER" : 2,
    "SSC_MOD_AMOUNT_0P4_CENTER" : 3,
    "SSC_MOD_AMOUNT_1P0_DOWN" : 4,
    "SSC_MOD_AMOUNT_1P5_DOWN" : 5,
    "SSC_MOD_AMOUNT_2P0_DOWN" : 6,
    "SSC_MOD_AMOUNT_3P0_DOWN" : 7,
}

ssc_mod_amount_inv = {val: key for key, val in ssc_mod_amount.items()}

ssc_mod_freq = {
    "SSC_MOD_FREQ_5680" : 0,
    "SSC_MOD_FREQ_5412" : 1,
    "SSC_MOD_FREQ_5144" : 2,
    "SSC_MOD_FREQ_4876" : 3,
    "SSC_MOD_FREQ_4608" : 4,
    "SSC_MOD_FREQ_4340" : 5,
    "SSC_MOD_FREQ_4072" : 6,
    "SSC_MOD_FREQ_3804" : 7,
    "SSC_MOD_FREQ_3536" : 8,
    "SSC_MOD_FREQ_3286" : 9,
    "SSC_MOD_FREQ_3000" : 10,
    "SSC_MOD_FREQ_2732" : 11,
    "SSC_MOD_FREQ_2464" : 12,
    "SSC_MOD_FREQ_2196" : 13,
    "SSC_MOD_FREQ_1928" : 14,
    "SSC_MOD_FREQ_1660" : 15,
}

ssc_mod_freq_inv = {val: key for key, val in ssc_mod_freq.items()}

class cdce906_cfg_struct(ctypes.Structure):
    _fields_ = [("clk_src", ctypes.c_int),
                ("pll_div_m", ctypes.c_ushort * 3),
                ("pll_div_n", ctypes.c_ushort * 3),
                ("pll_vco_mux", ctypes.c_int * 3),
                ("pll_fvco", ctypes.c_int * 3),
                ("ssc_mod_amount", ctypes.c_int),
                ("ssc_mod_freq", ctypes.c_int),
                ("s0_cfg", ctypes.c_int),
                ("s1_cfg", ctypes.c_int),
                ("pll_sel", ctypes.c_int * 6),
                ("p_div", ctypes.c_char * 6),
                ("y_slew", ctypes.c_int * 6),
                ("y_p_sel", ctypes.c_int * 6),
                ("y_out", ctypes.c_int * 6)]

class cdce906():
    def __init__(self, bus_number, slave_addr, lib_path="libcdce906.so"):
        try:
            libcdce906 = ctypes.cdll.LoadLibrary(lib_path)
        except:
            lib_path = glob.glob(os.path.dirname(os.path.realpath(__file__)) + "/../libcdce906*.so")[0]
            libcdce906 = ctypes.cdll.LoadLibrary(lib_path)

        self._cdce906_read_cfg = libcdce906.cdce906_read_cfg
        self._cdce906_read_cfg.argstypes = [ctypes.c_char_p, ctypes.POINTER(cdce906_cfg_struct)]
        self._cdce906_read_cfg.restype = ctypes.c_int

        self._cdce906_write_cfg = libcdce906.cdce906_write_cfg
        self._cdce906_write_cfg.argstypes = [ctypes.c_char_p, ctypes.POINTER(cdce906_cfg_struct)]
        self._cdce906_write_cfg.restype = ctypes.c_int

        self._bus = smbus2.SMBus(bus_number)
        self._slave_addr = slave_addr

    def get_cfg(self):
        cfg_struct = cdce906_cfg_struct()
        data = self._bus.read_i2c_block_data(self._slave_addr, 0x00, 27)
        self._cdce906_read_cfg(bytes(data), ctypes.byref(cfg_struct))
        cfg = {
            "clk_src" : clk_src_inv[cfg_struct.clk_src],
            "pll_div_m" : list(cfg_struct.pll_div_m),
            "pll_div_n" : list(cfg_struct.pll_div_n),
            "pll_vco_mux" : list(map(pll_vco_mux_inv.get, cfg_struct.pll_vco_mux)),
            "pll_fvco" : list(map(pll_fvco_inv.get, cfg_struct.pll_fvco)),
            "ssc_mod_amount" : ssc_mod_amount_inv[cfg_struct.ssc_mod_amount],
            "ssc_mod_freq" : ssc_mod_freq_inv[cfg_struct.ssc_mod_freq],
            "s0_cfg" : s0_cfg_inv[cfg_struct.s0_cfg],
            "s1_cfg" : s1_cfg_inv[cfg_struct.s1_cfg],
            "pll_sel" : list(map(px_pll_sel_inv.get, cfg_struct.pll_sel)),
            "p_div" : list(cfg_struct.p_div),
            "y_slew" : list(map(yx_slew_cfg_inv.get, cfg_struct.y_slew)),
            "y_p_sel" : list(map(yx_px_sel_inv.get, cfg_struct.y_p_sel)),
            "y_out" : list(map(yx_out_cfg_inv.get, cfg_struct.y_out)),
        }
        return cfg

    def set_cfg(self, cfg, write_eeprom=False):
        cfg_struct = cdce906_cfg_struct()
        data = bytes([0x00] * 28)
        cfg_struct.clk_src = clk_src[cfg["clk_src"]]
        cfg_struct.ssc_mod_amount = ssc_mod_amount[cfg["ssc_mod_amount"]]
        cfg_struct.ssc_mod_freq = ssc_mod_freq[cfg["ssc_mod_freq"]]
        cfg_struct.s0_cfg = s0_cfg[cfg["s0_cfg"]]
        cfg_struct.s1_cfg = s1_cfg[cfg["s1_cfg"]]
        cfg_struct.pll_div_m = (ctypes.c_ushort * 3)(*cfg["pll_div_m"])
        cfg_struct.pll_div_n = (ctypes.c_ushort * 3)(*cfg["pll_div_n"])
        cfg_struct.p_div = bytes(cfg["p_div"])
        cfg_struct.pll_vco_mux = (ctypes.c_int * 3)(*map(pll_vco_mux.get, cfg["pll_vco_mux"]))
        cfg_struct.pll_fvco = (ctypes.c_int * 3)(*map(pll_fvco.get, cfg["pll_fvco"]))
        cfg_struct.pll_sel = (ctypes.c_int * 6)(*map(px_pll_sel.get, cfg["pll_sel"]))
        cfg_struct.y_slew = (ctypes.c_int * 6)(*map(yx_slew_cfg.get, cfg["y_slew"]))
        cfg_struct.y_p_sel = (ctypes.c_int * 6)(*map(yx_px_sel.get, cfg["y_p_sel"]))
        cfg_struct.y_out = (ctypes.c_int * 6)(*map(yx_out_cfg.get, cfg["y_out"]))
        self._cdce906_write_cfg(bytes(data), ctypes.byref(cfg_struct))
        msg = smbus2.i2c_msg.write(self._slave_addr, data)
        self._bus.i2c_rdwr(msg)
        if write_eeprom:
            eereg = bytes([0x80 | 27])
            self._bus.write_i2c_block_data(self._slave_addr, 0x80 | 26, eereg)
