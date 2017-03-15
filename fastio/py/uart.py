import sys
from magma import *
from mantle import *
from rom import ROM
from mantle.lattice.mantle40.MUX import Mux4
from mantle.lattice.mantle40.register import _RegisterName, Register
from boards.icestick import IceStick

def DefineUART (n, init=0, ce=False, r=False, s=False):

  class _UART(Circuit):
    """Construct a UART connection, specifically for FPGA -> CPU sending"""
    """Inputs:  data : BYTE, valid : BIT"""
    """Outputs: TX : BIT, ready : BIT"""
    """We want to abstract away whether the UART is running faster or
    slower than the user, so for maximum generality we currently use a system
    of ACKs to talk around the clock divide"""
    """TODO get rid of some unnecessary arguments here, they don't make sense"""
    name = _RegisterName('UART', n, init, ce, r, s)
    IO = ["data", In(Array(8,Bit)), "valid", In(Bit), "TX", Out(Bit), "ready", Out(Bit)] + ClockInterface(ce,r,s)

    @classmethod
    def definition(uart):
      baud = 1

      #Convenience
      valid = uart.valid

      #The protocol for handling the baudrate of the UART is as follows:
      # - inputs are immediately latched on the user clock
      # - RequestAck is toggled
      # - When RequestAck != Ack and the UART is ready to print, load the
      #   latched byte into the PISO
      # - After loading the byte into the PISO, Ack is toggled.
      # -- At this point, again, RequestAck == Ack and the process repeats
      #
      #This handshake allows the UART and the user code to be in
      #entirely different clock domains. It is also simpler than reasoning
      #about when to latch a user input based on some ready / done bits.

      #User clock domain
      ready = DFF()
      RequestAck = DFF()

      #UART clock domain (i.e. at baudrate)
      running = DFF(ce=True)
      Ack = DFF(ce=True)

      #"Send" protocol across the clock divide, i.e. latch the printf input and
      #deassert ready
      should_send = LUT2(I0 & I1)(ready, valid)

      #This latches the data @ the user clock. We move this to a PISO below on
      #the next baud cycle after should_send_request goes high.
      data = Register(8, ce=True)
      data(uart.data)
      wire(should_send, data.CE)

      #Send the request one cycle lagged behind should_send just to ward off clock
      #domain problems
      #SHOULD SEND ACK register
      should_send_request = DFF()
      should_send_request(should_send)

      #~ready & (requestAck==Ack) & ~should_send_request
      should_ready = LUT4(~I0 & ~(I1^I2) & ~I3)(ready, RequestAck, Ack, should_send_request)

      ready_n = LUT3((I0 & ~I1) | I2)(ready, should_send, should_ready)

      #READY register
      wire(ready_n, ready.I)

      request_ack_n = LUT2(I0 ^ I1)(RequestAck, should_send_request)
      #REQUEST ACK register
      wire(request_ack_n, RequestAck.I)


      # Cycle through UART bit-protocol
      count    = Counter(4, ce=True, r=True)

      # TODO decode is heavyweight!
      done     = Decode(15, 4)(count)

      #Send the ack one cycle after copying into the piso. Again, this is
      #to ward off clock domain problems.
      should_send_ack = DFF(ce=True)
      wire(baud, should_send_ack.CE)

      #~running & (requestAck != Ack) & ~should_send_ack
      should_run = LUT4(~I0 & (I1^I2) & ~I3)(running, RequestAck, Ack, should_send_ack)
      running_n = LUT3((I0 & ~I1) | I2)(running, done, should_run)
      running(running_n)
      wire(baud, running.CE)

      should_send_ack(should_run)

      ack_n = LUT2(I0 ^ I1)(Ack, should_send_ack)
      Ack(ack_n)
      wire(baud, Ack.CE)

      #Load the piso on should_run
      shift = PISO(9, ce=True)
      load  = should_run
      shift(1,array(data.O[7],data.O[6],data.O[5],data.O[4],data.O[3],data.O[2],data.O[1],data.O[0],0),load)
      wire(baud,shift.CE)

      #Reset count whenever done or not running.
      #Resetting on just ~running is too conservative and wastes a cycle since
      #we can reset on done too
      reset = LUT2(I0 | ~I1)(done, running_n)
      count(CE=baud, RESET=reset)

      # Wire shift output to TX
      wire(shift, uart.TX)
      #wire(ready, uart.ready)
      wire(ready, uart.ready)

  return _UART

def UART(n, init=0, ce=False, r=False, s=False, **kwargs):
    return DefineUART(n, init, ce, r, s)(**kwargs)

