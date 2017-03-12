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
    IO = ["data", In(Bit), "data_done", In(Bit), "valid", In(Bit), "TX", Out(Bit), "busy", Out(Bit), "ready", Out(Bit)] + ClockInterface(ce,r,s)

    @classmethod
    def definition(uart):

      baud = 1
      logn = 4

      # Transmit 16 bits per UART packet
      count    = Counter(logn, ce=True, r=True)
      done     = Decode(15, logn)(count)
      # Transmit [0, next 8 data input, 1, 1, 1, 1, 1, 1, 1] and then repeat
      # Tack on 1 bit head and 7 bit tail
      # disable ready out during head and tail bit to stall data_in
      head_bit = EQ(4)(count, array(0,0,0,0)) # BIT 0 is head bit
      tail_bit = UGT(4)(count, array(0,0,0,1)) # BIT 9,10,11,12,13,14,15 are tail bit

      # After 16-bit UART, transition run from 1->0 for 1 cycle and then start next block
      run   = DFF(ce=True)
      run_n = LUT3([0,0,1,0, 1,0,1,0])
      run_n(done, uart.valid, run)
      run(run_n)
      wire(baud, run.CE)

      # After 16 bits, reset counter to send out next UART packet
      reset = LUT2((I0&~I1))(done, run)
      count(CE=baud, RESET=reset)

      # Busy if either uart 16-bit state machine is running OR data is not yet done
      busy  = LUT2(I0 | ~I1)(run, uart.data_done)
      wire(busy, uart.busy)

      # Ready to receive new data if uart 16-bit FSM is running && (!head bit && !tail bit)
      ready = LUT3(I0 & ~I1 & ~I2)(run,head_bit,tail_bit)
      wire(ready, uart.ready)

      # For now just pipe input data to output data
      # if head_bit -> pipe 0 out ; tail_bit -> pipe 1 out ; else data out
      mux4 = Mux4()
      mux4(array(uart.data,0,1,1),array(head_bit,tail_bit))
      wire(mux4.O, uart.TX)
  return _UART

def UART(n, init=0, ce=False, r=False, s=False, **kwargs):
    return DefineUART(n, init, ce, r, s)(**kwargs)

