from magma import *
from mantle import *
from uart import UART
import json

def CacheWrapper(namefunc, func, *args):
        if not hasattr(func, "cache"):
                func.cache = {}
        name = namefunc(*args)
        assert name
        if name in func.cache:
                return func.cache[name]
        value = func(*args, name=name)
        assert value
        func.cache[name] = value
        return value

def _DisplayName(width, height, bpp):
        return "Display_%d_%d_%d" % (width,height,bpp)

reliable_uart_extension = True
def _DefineDisplay(width, height, bpp, name):
        interface = [
                #Communication with user graphics
                "x", Out(Array(bpp,Bit)),
                "y", Out(Array(bpp,Bit)),
                "framecount", Out(Array(8,Bit)),
                "ready", Out(Bit),
                "valid", In(Bit),
                "pixel", In(Array(bpp,Bit)),

                #Communication with PC
                "DTR", In(Bit),

                #Communication with UART
                "ready_out", In(Bit),
                "data_out", Out(Array(8,Bit)),
                "valid_out", Out(Bit)

        ] + ClockInterface(ce=False, r=True, s=False)

        Display = DefineCircuit(name, *interface)

        #width_n = log2(width)
        #if ((1 << width_n) < width):
        #        width_n = width_n + 1

        #height_n = log2(height)
        #if ((1 << height_n) < height):
        #        height_n = height_n + 1
        width_n = 8
        height_n = 8

        x_cnt = CounterModM(width, width_n, r=True, ce=True)
        y_cnt = CounterModM(height, height_n, r=True, ce=True)
        frame_count = Counter(8, r=True, ce=True)

        stream_has_more_space = 1

        #We can make the UART reliable, but it requires some cooperation with the
        #user program. Specifically, the user program must ACK every time it
        #reads a buffer from us, by rising-edge the DTR line
        resetSignal = Display.RESET
        if (reliable_uart_extension):
                BytesSent = Register(16, r=True, ce=True)
                BytesSent_n = Add(16)
                BytesSent_n(BytesSent, array(*int2seq(1, 16)))
                BytesSent(BytesSent_n.O)
                #See condition for sending a byte below
                wire(LUT3((I0 & I1)|I2)(Display.ready_out, Display.valid, resetSignal),BytesSent.CE)
                wire(resetSignal, BytesSent.RESET)

                #Listen to ACKs via rising edge of DTR register.
                #Can't just compute rising edge as ~DTRbuffer & printf.DTR due to
                #glitches! The rising edge is only correctly detected if we buffer
                #again.
                DTRBuffer = DFF()
                DTRBuffer(Display.DTR)
                DTRBuffer_lag = DFF()
                DTRBuffer_lag(DTRBuffer)
                DTRRising = LUT2(~I0 & I1)(DTRBuffer_lag, DTRBuffer)

                #Each ACK acks this many bytes read from the stream:
                bufferSize = 510*8

                BytesAcked = Register(16, r=True,ce=True)
                BytesAcked_n = Add(16)
                BytesAcked_n(BytesAcked, array(*int2seq(bufferSize, 16)))
                BytesAcked(BytesAcked_n.O)
                wire(resetSignal, BytesAcked.RESET)
                wire(LUT2(I0 | I1)(DTRRising, resetSignal),BytesAcked.CE)

                BytesInFlight = Sub(16)
                BytesInFlight(BytesSent, BytesAcked)

                stream_has_more_space = ULT(16)(
                                BytesInFlight.O,
                                array(*int2seq(bufferSize*2 - 8,16))
                )

                #Useful debugging:
                #wire(array(*[BytesInFlight.O[i] for i in range(8)]), Display.data_out)
                #wire(array(*[BytesSent.O[i] for i in range(8)]), Display.data_out)

        should_emit = LUT3(I0 & I1 & ~I2)(Display.ready_out, Display.valid, stream_has_more_space)

        wire(LUT2(I0 | I1)(should_emit, resetSignal), x_cnt.CE)
        wire(0, y_cnt.CE)
        wire(0, frame_count.CE)

        wire(resetSignal, x_cnt.RESET)
        wire(resetSignal, y_cnt.RESET)
        wire(resetSignal, frame_count.RESET)

        wire(x_cnt.O, Display.x)
        wire(y_cnt.O, Display.y)
        wire(frame_count.O, Display.framecount)

        #Just pipe user output to the uart
        wire(should_emit, Display.valid_out)
        wire(Display.pixel, Display.data_out)

        EndCircuit()

        return Display

def DefineDisplay(*args):
        return CacheWrapper(
                _DisplayName,
                _DefineDisplay,
                *args
        )

#Create a display with a connection
def _DefineDisplayConn(connection,width,height,bpp,name):
        interface = [
                "x", Out(Array(bpp,Bit)),
                "y", Out(Array(bpp,Bit)),
                "framecount", Out(Array(8,Bit)),
                "ready", Out(Bit),
                "valid", In(Bit),
                "pixel", In(Array(bpp,Bit)),
                "DTR", In(Bit),
                "TX", Out(Bit),
        ] + ClockInterface(ce=False, r=True, s=False)

        DisplayConn = DefineCircuit(name, *interface)

        #Create UART connection
        if connection == "UART":
                conn = UART(1,0)
        else:
                raise ValueError("Only support UART for now")

        display = DefineDisplay(width, height, bpp)()

        # Expose display wires to user program
        wire(display.x, DisplayConn.x)
        wire(display.y, DisplayConn.y)
        wire(display.framecount, DisplayConn.framecount)
        wire(display.ready, DisplayConn.ready)
        wire(DisplayConn.valid, display.valid)
        wire(DisplayConn.pixel, display.pixel)
        wire(DisplayConn.DTR, display.DTR)
        wire(DisplayConn.RESET, display.RESET)

        # Hook up to uart connection type
        wire(display.valid_out, conn.valid)
        wire(display.data_out, conn.data)
        wire(conn.ready,  display.ready_out)

        # Wire the UART output to top level
        wire(conn.TX, DisplayConn.TX)

        EndCircuit()

        return DisplayConn

def _DisplayConnName(conn,width,height,bpp):
        return "DisplayConn_%s_%d_%d_%d" % (conn,width,height,bpp)

def DisplayConn(f, conn, width, height, bpp):
        DisplayT = CacheWrapper(
                _DisplayConnName,
                _DefineDisplayConn,
                conn, width, height, bpp
        )

        json_data = {
                'type': 'display',
                'width': width,
                'height': height,
                'bpp': bpp
        }
        json.dump(json_data, f, indent=2)
        f.write("\n")

        return DisplayT()
