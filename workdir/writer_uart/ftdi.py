import sys
from magma import *
from mantle import *
from rom import ROM
from boards.icestick import IceStick

icestick = IceStick()
icestick.Clock.on()
icestick.TX.output().on()
icestick.RX.input().on()
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

# Temp place to store the output
buffer = Register(9)

logn = 4

#printf = Counter(logn, ce=True, r=True)
#rom = ROM(logn, init, printf.O)

#data = array(rom.O[7], rom.O[6], rom.O[5], rom.O[4],
#             rom.O[3], rom.O[2], rom.O[1], rom.O[0], 0 )

#This achieves 115200 hz
clock = CounterModM(103, 8)

#Double speed
#clock = CounterModM(52, 8)

#Half of max speed (12MHz)
#clock = CounterModM(2, 2)

#Max speed the linux FTDI driver supports (3MHz)
# (= 1/4 clock rate)
#clock = CounterModM(4, 8)

baud = clock.COUT

#baud always on = max clock rate
#baud = 1

# Generate start signal (detect high->low transition)
start_dff = DFF(ce=True,r=True)
rx_inv    = LUT1(~I0)
start     = And2()
rx_inv(main.RX)
start_dff(main.RX)
start(rx_inv, start_dff)
wire(baud, start_dff.CE)

# Cycle through the expected length of transfer (fixed to 16 for now)
count = Counter(logn, ce=True, r=True)
done  = Decode(15, logn)(count)

run   = DFF(ce=True)
run_n = LUT3([0,0,1,0, 1,0,1,0])
run_n(done, run, start)
run(run_n)
wire(baud, run.CE)

start_reset = LUT2((~I0&I1))(done, run)
reset = LUT2((I0&~I1))(done, run)
count(CE=baud, RESET=reset)

wire(start_reset, start_dff.RESET)

#We are abusing RTS as a kind of reset signal. When it is set, reset to the
#first character of the printf and don't output any bytes until it becomes
#unset. This has no relation to the usual use of RTS in UARTs.

#Load of the shift register is what actually causes the current character of printf
#to be written out over the next few cycles and lead to interrupts
#
#valid / run will continue to tick even with main.RTS set, but we won't start
#the shift register.
shift = SIPO(9, ce=True, r=True)
load = LUT2(I0&~I1)(valid,run)
shift(main.RX, CE=baud, RESET=load)

#Ready is what causes us to advance the printf to the next character
#ready = LUT2(~I0 & I1)(run, baud)
#printf(CE=ready, RESET=main.RTS)

wire(shift.O, buffer.I)

wire(buffer.O[0], main.D1)
wire(buffer.O[1], main.D2)
wire(buffer.O[2], main.D3)
wire(buffer.O[3], main.D4)
wire(buffer.O[4], main.D5)

compile(sys.argv[1], main)

