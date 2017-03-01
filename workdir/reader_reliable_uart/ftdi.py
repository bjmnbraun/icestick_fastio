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

def my_baud():
        return 1

baud = my_baud()

PACKETSIZE = 510 * 8
N = PACKETSIZE
logn = log2(N)+1

assert((1<<logn)>N)

printf = Counter(logn, ce=True, r=True)
init = [array(*int2seq(ord(c), 8)) for c in 'Hello, world!  \n']
rom = ROM(4, init, printf.O[0:4])
data = array(rom.O[7], rom.O[6], rom.O[5], rom.O[4],
             rom.O[3], rom.O[2], rom.O[1], rom.O[0], 0 )

more_bytes_in_packet = NE(logn)(printf.O, array(*int2seq(N,logn)))

should_write_byte = more_bytes_in_packet

DTRbuffer = DFF(ce=True)
DTRbuffer(main.DTR)
wire(baud, DTRbuffer.CE)

DTRbuffer_lag = DFF(ce=True)
DTRbuffer_lag(DTRbuffer)
wire(baud, DTRbuffer_lag.CE)

DTRraised = LUT2(I0 & ~I1)(DTRbuffer, DTRbuffer_lag)

CanStartNewBuffer = DFF(ce=True)

StartNewBuffer = LUT2(I0 & ~I1)(CanStartNewBuffer, more_bytes_in_packet)

CanStartNewBuffer(LUT3((I0 | I1)&~I2)(CanStartNewBuffer, DTRraised, StartNewBuffer))
wire(baud, CanStartNewBuffer.CE)

RTSbuffer = DFF(ce=True)
RTSbuffer(main.RTS)
wire(baud, RTSbuffer.CE)

valid = LUT2(~I0 & I1)(RTSbuffer, should_write_byte)

#### UART PROTOCOL

#Pipeline has K stages
#Stage 0 waits for data / loads data
#Remaining stages pipe data out
count = Counter(4, ce=True, r=True)

load = LUT2(I0 & I1)(valid, Decode(0, 4)(count))
nodata = LUT2(~I0 & I1)(valid, Decode(0, 4)(count))

done = Decode(15, 4)(count)

reset = LUT2(I0 | I1)(done, nodata)
count(CE=baud, RESET=reset)

shift = PISO(9, ce=True)
shift(1,data,load)
wire(baud, shift.CE)

#### End uart protocol

#On a load, advance the printf
#Hack using CE can be counterintuitive because we also need to allow reset
printf_reset = LUT2(I0 | I1)(RTSbuffer, StartNewBuffer)
ready = LUT3((I0 | I1) & I2)(load, printf_reset, baud)
printf(CE=ready, RESET=printf_reset)

wire(shift, main.TX)

wire(main.RTS, main.D1)
wire(main.CTS, main.D2)
wire(main.DTR, main.D3)
wire(main.DSR, main.D4)
wire(CanStartNewBuffer, main.D5)

compile(sys.argv[1], main)

