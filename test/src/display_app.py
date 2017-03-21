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

width = 64
height = 64
#Grayscale for now
bpp = 8

def ProcGraphics():
        adder0 = Add(8)
        adder1 = Add(8)
        wire(adder0, adder1.I0)
        print(dir(adder1))
        _ignore = In(Bit)()
        _const1 = Out(Bit)()
        wire(1, _const1)
        return AnonymousCircuit(
                "x", adder0.I0,
                "y", adder0.I1,
                "framecount", adder1.I1,
                "ready", _ignore,
                "valid", _const1,
                "pixel", adder1.O
        )

graphics = ProcGraphics()
print("Graphics is", graphics)

display = fastio_simple_display(width, height, bpp)
print("Display is", display)
wire(display.x, graphics.x)
wire(display.y, graphics.y)
wire(display.framecount, graphics.framecount)
wire(display.ready, graphics.ready)
wire(graphics.pixel, display.pixel)
wire(graphics.valid, display.valid)

#Compilation hook - ideally magma would do this for us
fastio_compile_hook()
compile(sys.argv[1], main)

