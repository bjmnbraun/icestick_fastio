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

logn_data = 4
logn_char = 3

printf = Counter(logn_data, ce=True, r=True)
rom    = ROM(logn_data, init, printf.O)
count  = Counter(logn_char, ce=True, r=True)
count(RESET=main.RTS)
mux8   = Mux8()
mux8(rom.O,count)

#Ready is what causes us to advance the printf to the next character
printf(CE=count.COUT, RESET=main.RTS)

#baud always on = max clock rate
baud = 1
data_done = 0

# Get uart connection and feed in data
uart = UART(1,0)
uart();
wire(mux8.O,uart.data)
wire(data_done,uart.data_done)
wire(main.RTS,uart.valid)

# Only feed in data when uart is ready to accept data
wire(uart.ready, count.CE)

wire(uart.TX, main.TX)

wire(main.RTS, main.D1)
wire(main.CTS, main.D2)
wire(main.DTR, main.D3)
wire(main.DSR, main.D4)
wire(main.DCD, main.D5)

compile(sys.argv[1], main)

