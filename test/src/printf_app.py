import sys
from magma import *
from mantle import *
from rom import ROM
from rom import REGs
from uart import UART
from printf import IOPrintf
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

#Output looks like:
#04 02 42 35 02 42 35 03 04 05 04 05 42 35 01 42 35 02 03 04 42 35 05
#where the "42 35" is a message of type 1 and the rest are of type 0

#Note - CounterModM is broken in base magma, we have a patch to fix
_valid0 = CounterModM(7,8,cout=True)
valid0 = _valid0.COUT
#string0 = "Hello world    \n"
#data0 = array(*[x for c in string0 for x in int2seq(ord(c), 8)])
#length0 = len(string0)
data0 = array(*[x for c in [int2seq(42,8),int2seq(35,8)] for x in c])
length0 = 2

_valid1 = CounterModM(5,8,cout=True)
valid1 = _valid1.COUT
#string1 = "foobar         \n"
#data1 = array(*[x for c in string1 for x in int2seq(ord(c), 8)])
#length1 = len(string1)
#valid0 is ticking away at some other frequency, spy on it via this printf:
data1 = _valid0.O
length1 = 1

# Get uart connection
#  TODO args ignored
uart = UART(1,0)
uart();

# Get printf statement
printf = IOPrintf([length0, length1], ce=False, r=True)
printf(RESET=main.RTS,dtr=main.DTR)

wire(data0, printf.data0)
wire(data1, printf.data1)

# Set valid always for now (this is user defined circuit)
wire(valid0,  printf.valid0)
wire(valid1,  printf.valid1)

# Hook printf up to uart connection type
wire(printf.valid_out, uart.valid)
wire(printf.data_out,  uart.data)
wire(uart.ready,  printf.ready)

wire(uart.TX, main.TX)

wire(main.RTS, main.D1)
wire(main.CTS, main.D2)
wire(main.DTR, main.D3)
wire(main.DSR, main.D4)
wire(main.DCD, main.D5)

compile(sys.argv[1], main)

