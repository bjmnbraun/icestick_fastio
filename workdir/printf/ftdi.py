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

valid = 1
length = array(1,1)

# For now print out full statement
init = [array(*int2seq(ord(c), 8)) for c in 'a  \n']

# Get uart connection
uart = UART(1,0)
uart();

# Get printf statement
printf = IOPrintf(1, ce=False, r=True)
printf(RESET=main.RTS)

# Just wire up 4 characters to 4 arguments for now
wire(init[0], printf.data0_arg0)
wire(init[1], printf.data0_arg1)
wire(init[2], printf.data0_arg2)
wire(init[3], printf.data0_arg3)
wire(length, printf.length0)

# Set valid always for now (this is user defined circuit)
wire(valid,  printf.valid[0])

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

