import gc
import sys
import time
import board
import busio
from digitalio import Direction, DigitalInOut
import adafruit_bus_device.spi_device as spi_device
from Adafruit_CircuitPython_AT86RF233 import adafruit_at86rf233

spi_bus = busio.SPI(board.RF_SCK, MOSI=board.RF_MOSI, MISO=board.RF_MISO)
cs_pin = DigitalInOut(board.SEL) # Chip select of the AT86RF
sleep_pin = DigitalInOut(board.SLP_TR)
reset_pin = DigitalInOut(board.RESETN)

radio = adafruit_at86rf233.AT86RF233(spi_bus, cs_pin, sleep=sleep_pin, reset=reset_pin)

DEBUG = True

radio.channel = 25
if DEBUG:
    print("Radio channel ", radio.channel)

radio.short_addr = 0
radio.pan_addr = 0
radio.ieee_addr = [0, 0, 0, 0, 0, 0, 0, 0]
if DEBUG:
    print("Short address: ", hex(radio.short_addr))
    print("PAN address: ", hex(radio.pan_addr))
    print("IEEE address: ", [hex(i) for i in radio.ieee_addr])

radio._write_reg(0x17, [0B00000010])  # AACK_PROM_MODE - promisc mode
radio._write_reg(0x2E, [0B00010000])  # AACK_DIS_ACK - dont send ack frames ever
trx_ctrl0 = radio._read_reg(0x03)[0]
trx_ctrl0 |= 0B10000000 # TOM mode enabled
radio._write_reg(0x03, [trx_ctrl0])

led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

if DEBUG:
    print("Free memory: ", gc.mem_free())

while input("Send START command: ") != "START":
    pass
    
print("SNIF", end="")
stamp = time.monotonic()
while True:
    stat = radio.status
    irq = radio.irq
    status = adafruit_at86rf233.RTX_STATE[stat]
    if time.monotonic() - stamp > 3: # every n seconds, print status
        if DEBUG:
            print("@", time.monotonic(), " -- status: ", hex(stat), status, "IRQ: ", hex(irq))
        stamp = time.monotonic()

    if status == 'P_ON':
        #print("\tP_ON")
        radio._write_reg(0x0E, [1 << 4])  # Interrupt AWAKE_END (IRQ_4) enabled
        radio._write_reg(0x02, [adafruit_at86rf233.RTX_STATE.index('TRX_OFF')])      # Go from P_ON to TRX_OFF state
    if status == 'TRX_OFF':
        #print("\tTRX_OFF")
        radio._write_reg(0x0E, [1])  # PLL Lock irq_0 enabled
        radio._write_reg(0x02, [adafruit_at86rf233.RTX_STATE.index('TX_ON')])
    if irq & 0x1:
        #print("\tIRQ LOCK")
        radio._write_reg(0x0E, [0])  # Interrupts RX_START (IRQ_2), TRX_END (IRQ_3) and AMI (IRQ_5) enabled
        radio._write_reg(0x02, [adafruit_at86rf233.RTX_STATE.index('RX_AACK_ON')])
    if irq & 0x4:
        #print("\tIRQ RTX END")
        led.value = True
        frame = radio.read_frame()
        if DEBUG:
            print("Frame size ", len(frame), ":", [hex(i) for i in frame])
        else:
            x = sys.stdout.write(bytes(len(frame)))
            x = sys.stdout.write(frame)
        led.value = False