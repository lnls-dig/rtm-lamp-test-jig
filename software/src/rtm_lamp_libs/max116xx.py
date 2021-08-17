import smbus2

ref_sel = {
    "REF_VDD" : 0b0000000,
    "REF_EXT" : 0b0100000,
    "REF_INT_OFF" : 0b1000000,
    "REF_INT_ON" : 0b1010000,
    "REF_INT_OFF_OUT" : 0b1100000,
    "REF_INT_ON_OUT" : 0b1110000,
}

clk_sel = {
    "CLK_INT" : 0b0000,
    "CLK_EXT" : 0b1000,
}

pol_sel = {
    "UNIPOLAR" : 0b000,
    "BIPOLAR" : 0b100,
}

scan_mode = {
    "SCAN_FROM_AIN0" : 0b000000,
    "SCAN_OFF" : 0b010000,
    "SCAN_UPPER" : 0b100000,
    "SCAN_OFF_SINGLE_CONV" : 0b110000,
}

diff_mode = {
    "DIFFERENTIAL" : 0,
    "SINGLE_ENDED" : 1,
}

class max116xx():
    def __init__(self, bus_number, slave_addr):
        self._bus = smbus2.SMBus(bus_number)
        self._slave_addr = slave_addr

    def set_config(self, cfg_dict):
        cfg_data = [0x80, 0x00]
        cfg_data[0] |= ref_sel[cfg_dict["ref_sel"]]
        cfg_data[0] |= clk_sel[cfg_dict["clk_sel"]]
        cfg_data[0] |= pol_sel[cfg_dict["pol_sel"]]
        cfg_data[0] |= 0b10
        cfg_data[1] |= scan_mode[cfg_dict["scan_mode"]]
        cfg_data[1] |= (cfg_dict["channel_sel"] & 0x0F) << 1
        cfg_data[1] |= diff_mode[cfg_dict["diff_mode"]]
        msg = smbus2.i2c_msg.write(self._slave_addr, cfg_data)
        self._bus.i2c_rdwr(msg)

    def read(self, samples, bipolar=False):
        msg = smbus2.i2c_msg.read(self._slave_addr, 2 * samples)
        self._bus.i2c_rdwr(msg)
        data = []
        for i in range(samples):
            sample_bytes = msg.buf[2*i:2*i+2]
            data.append(int.from_bytes(sample_bytes, "big") & 0x03FF)
        return data
