# The MIT License (MIT)
#
# Copyright (c) 2018 ladyada for adafruit industries
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
`adafruit_at86rf233`
====================================================

CircuitPython/Python library for communicating via AT86RF233 radio chip

* Author(s): ladyada

Implementation Notes
--------------------

**Hardware:**

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases
* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
* Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""

import time
from micropython import const
from digitalio import Direction, DigitalInOut
import adafruit_bus_device.spi_device as spi_device

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_AT86RF233.git"


#pylint: disable=bad-whitespace
# Register and other constant values:
_READ_FRAME      = const(0x20)
_READ_REG        = const(0x80)
_WRITE_REG       = const(0xC0)
_REG_PART_NUM    = const(0x1C)
_REG_VERSION_NUM = const(0x1D)
_REG_SHORTADDR   = const(0x20)
_REG_PANADDR     = const(0x22)
_REG_IEEEADDR    = const(0x24)
_REG_PHYCCCCA    = const(0x08)

RTX_STATE = ('P_ON', 'BUSY_RX', 'BUSY_TX', 'FORCE_TRX_OFF', # 0 - 3
             'FORCE_TX_ON', None, 'RX_ON', 'SUCCESS',       # 4 - 7
             'TRX_OFF', 'TX_ON', None, None,                # 8 - 11
             None, None, None, 'SLEEP',                     # 12 - 15
             'PREP_DEEP_SLEEP', 'BUSY_RX_AACK', 'BUSY_TX_ARET', None, #16-19
             None, None, 'RX_AACK_ON', None,                # 20 - 23
             None, 'TX_ARET_ON', None, None,                # 24 - 27
             'RX_ON_NOCLK', 'RX_AACK_ON_NOCLK',             # 28, 29
             'BUSY_RX_AACK_NOCLK', 'TRANSITION')            # 30, 31
            
             
#pylint: enable=bad-whitespace

class AT86RF233:
    """Driver for the AT86RF233 radio chipset."""

    # Class-level buffer for reading and writing data with the sensor.
    # This reduces memory allocations but means the code is not re-entrant or
    # thread safe!
    _BUFFER = bytearray(128)

    def __init__(self, spi, cs, *, sleep=None, reset=None):
        self._spi = spi_device.SPIDevice(spi, cs)
        if sleep:
            sleep.direction = Direction.OUTPUT
            sleep.value = False  # out of sleep mode
        if reset:
            reset.direction = Direction.OUTPUT
            reset.value = False
            time.sleep(0.01)
            reset.value = True
        time.sleep(0.01)
        part_num = self._read_reg(_REG_PART_NUM)[0]
        if part_num != 0x0b:
            raise RuntimeError("Part #0x%x wrong" % part_num)
        vers = self._read_reg(_REG_VERSION_NUM)[0]
        if vers != 2:
            raise RuntimeError("Version #%d wrong" % vers)

    def read_frame(self):
        with self._spi as spi:
            self._BUFFER[0] = _READ_FRAME
            spi.write_readinto(self._BUFFER, self._BUFFER, in_end=2, out_end=2)
            num = self._BUFFER[1]
            spi.write_readinto(self._BUFFER, self._BUFFER, in_end=num, out_end=num)
        return self._BUFFER[0:num]
    
    @property
    def status(self):
        return self._read_reg(0x01)[0] & 0x1F

    @property
    def irq(self):
        return self._read_reg(0x0F)[0]

    @property
    def short_addr(self):
        i = self._read_reg(_REG_SHORTADDR, 2)
        return i[0] << 8 | i[1]

    @short_addr.setter
    def short_addr(self, addr):
        self._write_reg(_REG_SHORTADDR, bytes([addr >> 8, addr & 0xFF]))

    @property
    def pan_addr(self):
        i = self._read_reg(_REG_PANADDR, 2)
        return i[0] << 8 | i[1]

    @pan_addr.setter
    def pan_addr(self, addr):
        self._write_reg(_REG_PANADDR, bytes([addr >> 8, addr & 0xFF]))

    @property
    def ieee_addr(self):
        return self._read_reg(_REG_IEEEADDR, 6)

    @ieee_addr.setter
    def ieee_addr(self, addr):
        if len(addr) != 8:
            raise ValueError("IEEE address must be 8 bytes")
        self._write_reg(_REG_IEEEADDR, addr)

    @property
    def channel(self):
        return self._read_reg(_REG_PHYCCCCA, 1)[0] & 0x1F

    @channel.setter
    def channel(self, chan):
        if chan > 0x1A or chan < 0x0B:
            raise ValueError("Invalid channel")
        self._write_reg(_REG_PHYCCCCA, [chan])
    
    def _write_reg(self, reg_addr, buf):
        # address is only 5 bits!
        self._BUFFER[0] = _WRITE_REG | (reg_addr & 0x3F)
        for i in buf:
            self._BUFFER[1] = i
            with self._spi as spi:
                #print("writing ", [hex (i) for i in self._BUFFER[0:2]])
                spi.write(self._BUFFER, end=2)
            self._BUFFER[0] += 1

    def _read_reg(self, reg_addr, num=1):
        # address is only 5 bits!
        addr = bytearray(1)
        for i in range(num):
            # increment each byte
            addr[0] = _READ_REG | (reg_addr+i & 0x3F)
            with self._spi as spi:
                spi.write(addr)
                spi.readinto(self._BUFFER, start=i, end=i+1)
                #print("reading $%02x: 0x%02X" % (addr[0] & 0x3F, self._BUFFER[i]))
        return self._BUFFER[0:num]
