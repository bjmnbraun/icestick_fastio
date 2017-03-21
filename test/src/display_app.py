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

fastio_setup(UART,sys.argv[1], RESET=main.RTS, DTR=main.DTR, TX=main.TX)

width = 2
height = 2
#Grayscale for now
bpp = 8

def MyProcGraphics():
        adder0 = Add(16)()
        adder1 = Add(16)()
        wire(adder0, adder1.I0)
        _ignore = In(Bit)()
        return AnonymousCircuit(
                "x", adder0.I0,
                "y", adder0.I1,
                "framecount", adder1.I1,
                "ready", _ignore,
                "valid", 1,
                "pixel", adder1.O
        )

display = fastio_simple_display(width, height, bpp)
wire(display.x, graphics.x)
wire(display.x, graphics.y)
wire(display.framecount, graphics.framecount)
wire(display.ready, graphics.ready)
wire(graphics.pixel, display.pixel)
wire(graphics.valid, display.valid)

#Compilation hook - ideally magma would do this for us
fastio_compile_hook()
compile(sys.argv[1], main)

