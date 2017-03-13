import sys
from magma import *
from mantle import *
from rom import ROM
from uart import UART
from boards.icestick import IceStick

icestick = IceStick()
icestick.Clock.on()
icestick.TX.output().on()
icestick.RTS.input().on()
icestick.CTS.input().on()
icestick.DTR.input().on()
icestick.DSR.input().on()
icestick.DCD.input().on()

icestick.D1.on()
icestick.D2.on()
icestick.D3.on()
icestick.D4.on()
icestick.D5.on()

main = icestick.main()

valid = 1

init = [array(*int2seq(ord(c), 8)) for c in 'Hello, world!  \n']

logn = 4

# print over length of message == 16
printf = Counter(logn, ce=True, r=True)
# index into ROM from printf counter
rom    = ROM(logn, init, printf.O)

#baud always on = max clock rate
baud = 1

# Get uart connection and feed in data
uart = UART(1,0)
uart();
wire(rom.O,uart.data)
wire(main.RTS,uart.valid)

#Ready is what causes us to advance the printf to the next character
printf(CE=uart.ready, RESET=main.RTS)

wire(uart.TX, main.TX)

wire(main.RTS, main.D1)
wire(main.CTS, main.D2)
wire(main.DTR, main.D3)
wire(main.DSR, main.D4)
wire(main.DCD, main.D5)

compile(sys.argv[1], main)

