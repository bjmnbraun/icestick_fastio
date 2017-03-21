import sys
from magma import *
from mantle import *
from fastio import *
from boards.icestick import IceStick

icestick = IceStick()
icestick.Clock.on()
icestick.TX.output().on()
icestick.RTS.input().on()
icestick.DTR.input().on()
#icestick.CTS.input().on()
#icestick.DSR.input().on()
#icestick.DCD.input().on()

icestick.D1.on()
icestick.D2.on()
#icestick.D3.on()
#icestick.D4.on()
#icestick.D5.on()

main = icestick.main()

# Debug ack/ready CPU mechanism
wire(main.RTS, main.D1)
wire(main.DTR, main.D2)

#### Demo Applications

# Note - CounterModM is broken in base magma, we have a patch to fix
_valid0  = CounterModM(7,3,cout=True)
_valid1  = CounterModM(13,4,cout=True)
_valid2  = CounterModM(23,5,cout=True)

counter  = Counter(8, r=True, cout=True)
counter(RESET=main.RTS)

#### End demo applications

fastio_setup(UART,sys.argv[1], RESET=main.RTS, DTR=main.DTR, TX=main.TX)

# Notes:
#  Works for 1,2,3 or 4 print statements with arbitrary bitwidth arguments
#  Input must be 'array' type: need to add Bit or array support
#  May be nice to add in 'rising edge detect' for valid input for demo
#  Need to think of a few good demo applications

printf(counter.COUT, "256 clock tick")
printf(_valid2.COUT, "Mod23 val %d Mod13 time %d collision %d", _valid2.O, counter.O, array(_valid1.COUT))
printf(_valid1.COUT, "Mod13 val %d Mod7 collision %d", _valid1.O, array(_valid0.COUT))
printf(_valid0.COUT, "Mod7 val %d", _valid0.O)

#Compilation hook - ideally magma would do this for us
fastio_compile_hook()
compile(sys.argv[1], main)

