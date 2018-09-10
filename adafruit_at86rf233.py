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
_READ_REG        = const(0x80)
_REG_PART_NUM    = const(0x1C)
_REG_VERSION_NUM = const(0x1D)
#pylint: enable=bad-whitespace

class AT86RF233:
    """Driver for the AT86RF233 radio chipset."""

    # Class-level buffer for reading and writing data with the sensor.
    # This reduces memory allocations but means the code is not re-entrant or
    # thread safe!
    _BUFFER = bytearray(32)

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
        part_num = self._read_reg(_REG_PART_NUM)
        if part_num != 0x0b:
            raise RuntimeError("Part #0x%x wrong" % part_num)
        vers = self._read_reg(_REG_VERSION_NUM)
        if vers != 2:
            raise RuntimeError("Version #%d wrong" % vers)
        

    def _read_reg(self, reg_addr):
        # address is only 5 bits!
        self._BUFFER[0] = _READ_REG | (reg_addr & 0x3F)
        with self._spi as spi:
            spi.write(self._BUFFER, end=1)
            spi.readinto(self._BUFFER, end=1)
        return self._BUFFER[0]
