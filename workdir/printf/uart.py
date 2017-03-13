import sys
from magma import *
from mantle import *
from rom import ROM
from mantle.lattice.mantle40.MUX import Mux4
from mantle.lattice.mantle40.register import _RegisterName, Register
from boards.icestick import IceStick

def DefineUART (n, init=0, ce=False, r=False, s=False):
  
  class _UART(Circuit):
    """Construct a UART connection"""
    """Inputs:  data : BIT, done : BIT, valid : BIT"""
    """Outputs: TX : BIT, run : BIT, ready : BIT"""
    name = _RegisterName('UART', n, init, ce, r, s)
    IO = ["data", In(Array(8,Bit)), "valid", In(Bit), "TX", Out(Bit), "ready", Out(Bit)] + ClockInterface(ce,r,s)

    @classmethod
    def definition(uart):

      baud = 1
      logn = 4

      # Latch data in at start of each packet and insert head bit (0)
      data_in = Register(9, ce=True)
      
      # Latch valid in at start of each packet
      valid_in = DFF(ce=True)
      
      # Cycle through UART packet
      count    = Counter(logn, ce=True, r=True)
      done     = Decode(15, logn)(count)

      # After 16-bit UART, transition run from 1->0 for 1 cycle and then start next block
      run   = DFF(ce=True)
      run_n = LUT3([0,0,1,0, 1,0,1,0])
      run_n(done, valid_in, run)
      run(run_n)
      wire(baud, run.CE)

      # After 16 bits, reset counter to send out next UART packet
      reset = LUT2((I0&~I1))(done, run)
      count(CE=baud, RESET=reset)

      # Shift out the 16-bit packet
      shift = PISO(9, ce=True)
      load  = LUT2(I0&~I1)(valid_in,run)
      shift(1,data_in,load)
      wire(baud, shift.CE)
      
      # Wire shift output to TX
      wire(shift, uart.TX)
      
      # Ready is set when UART packet finishes: allow new inputs and data latch
      ready = LUT2(~I0 & I1)(run, baud)
      wire(ready, uart.ready)
      
      # Only allow new data latch when ready is set
      valid_in(CE=ready)
      wire(uart.valid,valid_in.I)
      data_in(CE=ready)
      wire(array(uart.data[7], uart.data[6], uart.data[5], uart.data[4],
                 uart.data[3], uart.data[2], uart.data[1], uart.data[0], 0 ), data_in)
            
  return _UART

def UART(n, init=0, ce=False, r=False, s=False, **kwargs):
    return DefineUART(n, init, ce, r, s)(**kwargs)

