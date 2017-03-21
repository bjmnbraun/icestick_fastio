import sys
from magma import *
from mantle import *
from boards.icestick import IceStick
from math import cos, sin, pi
from fastio import *

icestick = IceStick()
icestick.Clock.on()
icestick.D1.on()
icestick.D2.on()
icestick.D3.on()
icestick.D4.on()
icestick.D5.on()

#For printf
icestick.TX.output().on()
icestick.RTS.input().on()
icestick.DTR.input().on()

# Modules

#Caching circuit definitions are more than an optimization - magma misbehaves
#if you use DefineCircuit with the same name twice.
#
#In fact, this wrapper can be used for caching any kind of function and we use
#it for more than just circuit definitions.
#
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

#Creates a PWM signal with duty cycle = a / 2^b
#where
# a is an b-bit input to the circuit (i.e. a can vary over time)
# b must be a compile-time constant (integer)
#
def _DefinePWMDynamic(b, name):
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

def _PWMDynamicName(b):
        return "PWMDynamic%d" % (b)

def DefinePWMDynamic(*args):
        return CacheWrapper(
                _PWMDynamicName,
                _DefinePWMDynamic,
                *args
        )

#A circuit outputting a PWM signal with duty cycle = a / 2^b
#where a is a compiler-time constant integer
def _DefinePWM(a, b, name):
        interface = [
                "signal", Out(Bit)
        ] + ClockInterface(False, False, False)

        PWM = DefineCircuit(name, *interface)

        pwmDynamic_t = DefinePWMDynamic(b)
        pwmDynamic = pwmDynamic_t()

        wire(constarray(a,b), pwmDynamic.a)
        wire(pwmDynamic.signal, PWM.signal)

        EndCircuit()

        return PWM

def _PWMName(a,b):
        return "PWM%d_%d" % (a,b)

def DefinePWM(*args):
        return CacheWrapper(
                _PWMName,
                _DefinePWM,
                *args
        )

CounterCache = {}

def _CounterName(name, n, ce, r, s):
    name += '%d' % n
    if ce: name += 'CE'
    if r:  name += 'R'
    if s:  name += 'S'
    return name

#
# Create an n-bit mod-m counter
#
# NOTE: Magma's CounterModM is broken since it computes the name incorrectly
# for different m but same n and it doesn't handle n >= 8, so I fix this here:
#
def MyDefineCounterModM(m, n, cin=False, cout=True, incr=1, next=False, ce=False):
    r = False
    s = False
    name = _CounterName('CounterMod%d' % m, n, ce, r, s)
    if name in CounterCache:
         return CounterCache[name]

    args = []
    if cin:
        args += ['CIN', In(Bit)]

    args += ["O", Array(n, Out(Bit))]
    if cout:
        args += ["COUT", Out(Bit)]

    args += ClockInterface(ce, r, s)

    CounterModM = DefineCircuit(name, *args)

    counter = Counter(n, cin=cin, cout=cout, incr=incr, next=next,
                   ce=ce, r=True, s=False)
    if (n >= 8):
        reset = EQ(n)(constarray(m - 1,n),counter)
    else:
        reset = Decode(m - 1, n)(counter)

    if ce:
        CE = In(Bit)()
        reset = And2()(reset, CE)
        # reset is sometimes called rollover or RO
        # note that we don't return RO in Counter

        # should also handle r in the definition

    wire(reset, counter.RESET) # synchronous reset

    if ce: 
        wire(CE, counter.CE)

    if cin:
        wire( CounterModM.CIN, counter.CIN )

    wire( counter.O, CounterModM.O )

    if cout:
        wire( reset, CounterModM.COUT )

    wire(CounterModM.CLK, counter.CLK)
    if hasattr(counter,"CE"):
        wire(CounterModM.CE, counter.CE)

    EndCircuit()

    CounterCache[name] = CounterModM
    return CounterModM

def MyCounterModM(m, n, cin=False, cout=True, incr=1, next=False, ce=False, **kwargs):
    return MyDefineCounterModM(m, n, cin=False, cout=True, incr=1, next=False, ce=False)(**kwargs)

#Constructs a circuit outputting a baud signal with period T clock cycles
# i.e. the signal is "up" on clock cycles numbered -1 mod T
# i.e. the signal has duty cycle 1/T
def _Baud(T, name):
        if (T <= 0):
                raise(ValueError("T must be positive"))
        #Compute how many bits are needed to represent T without overflow
        #for positive T (T can never be 0)
        #Handy function log2 in magma does this but watch out since
        #it only handles 32 bit numbers.
        logTp1 = log2(T) + 1
        if (T >= (1 << logTp1)):
                raise(AssertionError("logTceil incorrect"))

        interface = [
                "signal", Out(Bit)
        ] + ClockInterface(False, False, False)

        BAUD = DefineCircuit(name, *interface)

        counterModM = MyCounterModM(T, logTp1)

        wire(counterModM.COUT, BAUD.signal)

        EndCircuit()

        #Construct the defined circuit too - bauds are monolithic
        #we cache the constructed circuit and it will be returned on calls to
        #Baud().
        return BAUD()

def _BaudName(T):
        return "Baud%d" % (T)

def Baud(*args):
        return CacheWrapper(
                _BaudName,
                _Baud,
                *args
        )

#Constructs a 2^m entry ROM of arbitrary width
#where rom[2^m][n] array of compile-time-constant bits (python ints)
#
#Not possible (or useful) to define such a circuit and instantiate
#it multiple times because no good way to mangle the contents of rom into a
#name for the resulting circuit type
def ROMMxN(rom):
        m = log2(len(rom))
        assert (1<<m) == len(rom)
        # transpose - rom must be a sequence of sequences
        rom = zip(*rom)
        n = len(rom)

        #ROMN will fail if m is not a power of two
        def ROM(y):
                return ROMN(rom[y])

        rom_circuit = fork(col(ROM, n))

        I = In(Array(m,Bit))()
        rom_circuit(I)

        #Need to use anonymous here because each rom is different
        return AnonymousCircuit("I", I, "O", rom_circuit.O)

#Returns an n-bit integer waveform
#with period 2^t ticks of baud signal
#
#The particular waveform is hardcoded, currently it is a single cosine-like
#impulse starting at offset @offset with width 2^t/4
#
#n, t, offset are all compile time constant python ints
def _DefineWaveform(n, t, offset, name):
        interface = [
                "baud", In(Bit),
                "O", Array(n, Out(Bit))
        ] + ClockInterface(False, False, False)

        SIN = DefineCircuit(name, *interface)

        counter = Counter(t, ce=True)
        wire(SIN.baud, counter.CE)

        #Make a lookup table of size 2^t with ith entry =
        # int(s * -1)
        # where s is varies sinusoidally from 0 to 1 back to 0 with period 2^t
        # We can't have t be too large since we are making a lookup table

        #Useful for testing
        def blink(y):
                if (y % 2):
                        return 0
                else:
                        return 1<<(n-1)

        def sinwave(y):
                s = sin(y/16.0*2*pi)
                return int((s+1)/2 * ((1<<n) - 1))

        def coswave_lessfrequent(y):
                if (y < (1<<(t-1))):
                        s = cos(y/float(1<<(t-1))*2*pi)
                        negs = (1-s)/2
                        return int(negs*((1<<n) - 1))
                return 0

        #romValues = [sinwave(y) for y in range(16)]
        romValues = col(coswave_lessfrequent, 1<<t)
        #Cyclically rotate romValues "offset" many entries left
        #Rotation helper from this stackoverflow
        #http://stackoverflow.com/questions/9457832/python-list-rotation#9457864
        def rotate(l, n):
            return l[-n:] + l[:-n]

        romValuesRot = rotate(romValues, offset)

        print("INFO", "Waveform looks like ", romValuesRot)
        rom = ROMMxN([int2seq(x,n) for x in romValuesRot])
        rom(counter.O)

        print(rom.interface)

        wire(rom.O, SIN.O)

        EndCircuit()

        return SIN

def _WaveformName(n, t, offset):
        return "Waveform%d_%d_%d" % (n,t,offset)

def DefineWaveform(n, t, offset=0):
        return CacheWrapper(
                _WaveformName,
                _DefineWaveform,
                n,t,offset
        )

#Constructs a circuit outputting a PWM signal based on a waveform
#using a specified baud rate. All arguments are compile time constant python
#ints
def _PWMWaveform(baud, n, t, offset, name):
        #Construct the needed baud (if we haven't already)
        baud_circuit = Baud(baud)

        #Construct a waveform and link baud in
        waveform = DefineWaveform(n, t, offset)()
        waveform(baud_circuit)

        #Construct a pwm and link the waveform into it
        pwm = DefinePWMDynamic(n)()
        pwm(waveform)

        return pwm

def _PWMWaveformName(baud, n, t, offset):
        return "PWMWaveform%d_%d_%d_%d" % (baud, n, t, offset)

def PWMWaveform(baud, n, t, offset=0):
        return CacheWrapper(
                _PWMWaveformName,
                _PWMWaveform,
                baud, n, t, offset
        )

# End modules

main = icestick.main()
fastio_setup(UART,sys.argv[1], RESET=main.RTS, DTR=main.DTR, TX=main.TX)

#Main routine

n = 4
t = 6

#lightshow has H many frames, each frame specifies different waveforms
H = 4
log2H = log2(H)
assert (1<<log2H) == H
#Every tick of this baud we advance to the next frame
frame_rate = Baud(1<<26)

which_frame = Counter(log2H, ce=True)
wire(frame_rate, which_frame.CE)

#Print the new frame every time we change
#Yuck - Magma's counter doesn't give an easy way to get
#the next value without changing the semantics of the counter.
#We'd like to write:
#printf(frame_rate, "Switching to frame", which_frame.NEXT)
#Instead we write:
printf(delay(frame_rate, 1), "Switching to frame %d", which_frame.O)

#i picks one of the lights D1...D5 = 01234
#Outputs the position of light i in direction direction
#so light D1 has position 2 in direction L
# (positions go 012)
def light_index(direction, i):
        if (direction=="L"):
                positions = [2,1,0,1,1]
        elif (direction=="D"):
                positions = [1,0,1,2,1]
        elif (direction=="U"):
                positions = [1,2,1,0,1]
        elif (direction=="R"):
                positions = [0,1,2,1,1]
        else:
                assert False
        return positions[i]

#2 baud rates, one faster than the other
#Just to show that we can have bauds that aren't a power-of-two
bauds = [1<<18, (1<<18) / 3]

#Returns the waveform that should be shown for light i in frame "frame" of the
#show
def make_light_frame(frame, i):
        if (frame == 0):
                baud = bauds[0]
                offset = light_index("L", i)
        elif (frame == 1):
                baud = bauds[1]
                offset = light_index("R", i)
        elif (frame == 2):
                baud = bauds[0]
                offset = light_index("D", i)
        elif (frame == 3):
                baud = bauds[1]
                offset = light_index("U", i)
        else:
                assert False

        return PWMWaveform(baud, n, t, offset*8).signal

def make_light(i):
        def _make_light_frame(frame):
                return make_light_frame(frame, i)
        return array(*col(_make_light_frame, H))

#Make a 5 x H array of waveforms
waves = array(*col(make_light, 5))

#Create muxes that choose the waveform corresponding to which_frame for each
#light and wire the muxes to the lights
muxes = braid(col(Mux4,5), forkargs=['S'])
wire(waves, muxes.I)
wire(which_frame, muxes.S)
wire(muxes.O, array(main.D1, main.D2, main.D3, main.D4, main.D5))

#End of main routine

fastio_compile_hook()
compile(sys.argv[1], main)
