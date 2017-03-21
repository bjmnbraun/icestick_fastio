from magma import *
from mantle import *

UART = 1

#Yeesh. These should be built-ins into magma since they are so useful!

#
#def edge(signal):
#       return (some circuit computing rising edge of signal)

def delay(signal, n):
        toRet = signal

        for i in range(n):
                ff = DFF()
                wire(toRet, ff.I)
                toRet = ff.O

        return toRet
