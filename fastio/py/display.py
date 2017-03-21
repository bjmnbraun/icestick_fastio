from magma import *
from mantle import *

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

#Create a display with a connection
def _DefineDisplayConn(conn,width,height,bpp):
        interface = [
                "a", In(Array(b,Bit)),
                "signal", Out(Bit)
        ] + ClockInterface(False, False, False)

        PWM = DefineCircuit(name, *interface)

        counter = Counter(b)

        lessthana = ULT(b)(counter.O, PWM.a)

        wire(lessthana, PWM.signal)

        EndCircuit()

        return PWM

def _DisplayConnName(conn,width,height,bpp):
        return "DisplayConn_%s_%d_%d_%d" % (conn,width,height,bpp)

def DefineDisplayConn(*args):
        return CacheWrapper(
                _DisplayConnName,
                _DefineDisplayConn,
                *args
        )

                RESET=connection['RESET'],
                DTR=connection['DTR'],
                TX=connection['TX']
