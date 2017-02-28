import sys
from magma import *
from mantle import *
from rom import ROM
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

printf = Counter(logn, ce=True)
rom = ROM(logn, init, printf.O)

data = array(rom.O[7], rom.O[6], rom.O[5], rom.O[4],
             rom.O[3], rom.O[2], rom.O[1], rom.O[0], 0 )

#This achieves 115200 hz
#clock = CounterModM(103, 8)

#Double speed
#clock = CounterModM(52, 8)

#Half of max speed (12MHz)
#clock = CounterModM(2, 2)

#Max speed the linux FTDI driver supports (3MHz)
# (= 1/4 clock rate)
#clock = CounterModM(4, 8)

#baud = clock.COUT

#baud always on = max clock rate
baud = 1

count = Counter(logn, ce=True, r=True)

#XXX
done = Decode(15, logn)(count)

run = DFF(ce=True)
run_n = LUT3([0,0,1,0, 1,0,1,0])
run_n(done, valid, run)
run(run_n)
wire(baud, run.CE)

reset = LUT3((I0&~I1)|I2)(done, run, main.RTS)
count(CE=baud, RESET=reset)

shift = PISO(9, ce=True)
load = LUT2(I0&~I1)(valid,run)
shift(1,data,load)
wire(baud, shift.CE)

ready = LUT2(~I0 & I1)(run, baud)
wire(ready, printf.CE)

wire(shift, main.TX)

wire(main.RTS, main.D1)
wire(main.CTS, main.D2)
wire(main.DTR, main.D3)
wire(main.DSR, main.D4)
wire(main.DCD, main.D5)

compile(sys.argv[1], main)

