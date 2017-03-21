import sys
import json
from magma import *
from mantle import *
from rom import ROM
from rom import RAM
from uart import UART
from mantle.lattice.mantle40.MUX import Mux4
from mantle.lattice.mantle40.register import _RegisterName, Register
from mantle.lattice.mantle40.compare import LT
from boards.icestick import IceStick

PrintValids = {}
PrintLens   = {}
PrintDatas  = {}

def REGs(n):
    return [Register(8, ce=True) for i in range(n)]

#Pads init[0] to the end of init until init has length == n
def pad_garbage(init, n):
    return array(*[init[i] if i < len(init) else init[0] for i in range(n)])

def PrintIO (f, valid, msg, *argv):

  header_bitwidth = 8
  
  idx  = len(PrintLens)
  args = ["I", In(Bit)]
  
  PrintValids[idx] = valid

  # Attach 8-bit header which is just index for now and concatenate to the input args
  PrintDatas[idx] = array(*[x for c in [int2seq(idx,header_bitwidth)] for x in c])
  for arg in argv:
    PrintDatas[idx] = concat(PrintDatas[idx], arg)

  # ceiling length to nearest multiple of 8 and zero pad the input to the length
  PrintLens[idx]  = (len(PrintDatas[idx]) + 7) >> 3
  PrintDatas[idx] = pad_garbage(PrintDatas[idx], PrintLens[idx] * 8)
  
  if 0:
    print(PrintLens[idx])
    print(PrintDatas)
    print(len(PrintDatas[idx]))

  # dump CPU side information to JSON file - message, total packet length, header bitwidth, argument bitwidth
  json_data = {'type': 'printf', 'msg' : msg, 'total_byte_len' : PrintLens[idx], 'header_bitwidth' : header_bitwidth, 'arg_bitwidths' : [len(arg) for arg in argv]}
  json.dump(json_data, f, indent=2)
  f.write("\n")
  
  return 0

def DefinePrintIOConn(connection, ce=False, r=False, s=False):

  n = len(PrintLens)
  init = 0

  class _IOPrintIOConn(Circuit):
    name = _RegisterName('IOPrintIOConn', n, init, ce, r, s)
    
    # fixed input/output to printIO
    IO = ["DTR", In(Bit), "TX", Out(Bit)] + ClockInterface(ce,r,s)
    
    # per print statement input/output to printIO
    for i in PrintLens:
      IO += ["valid%d"%i, In(Bit)]

    for i in PrintDatas:
      IO += ["data%d"%i, In(Array(len(PrintDatas[i]),Bit))]

    @classmethod
    def definition(printfconn):
      # Create UART and printf and hook it all up
      if connection == "UART":
        conn = UART(1,0)
        conn();
      else:
        assert(0)

      # Create printf with input length array and hook up RESET/DTR
      printf = IOPrintf([PrintLens[i] for i in PrintLens], ce=ce, r=r)
      printf(RESET=printfconn.RESET,DTR=printfconn.DTR)
      
      # Wire up the valid and data fields to printf
      for i in PrintLens:
        wire(getattr(printfconn,"valid%d"%i), getattr(printf,"valid%d"%i))
        wire(getattr(printfconn,"data%d"%i),  getattr(printf,"data%d"%i))

      # Hook printf up to uart connection type
      wire(printf.valid_out, conn.valid)
      wire(printf.data_out,  conn.data)
      wire(conn.ready,  printf.ready)
      
      # Wire the UART output to top level
      wire(conn.TX, printfconn.TX)

  return _IOPrintIOConn
  

def PrintIOConn(connection, ce=False, r=False, s=False, **kwargs):
    circuit = DefinePrintIOConn(connection, ce, r, s)(**kwargs)
    for i in PrintValids:
      wire(PrintValids[i], getattr(circuit,"valid%d"%i))
      wire(PrintDatas[i],  getattr(circuit,"data%d"%i))
      
    return circuit

def DefineIOPrintf (lengths, ce=False, r=False, s=False):

  #Sets whether to obey backpressure i.e. be robust
  reliable_uart_extension = True

  n = len(lengths)
  init = 0

  class _IOPrintf(Circuit):
    """Construct a printf IO type"""
    """Inputs:  valid : Array(n,Bit), length : Array(n,Array(4,Bit)),
      arg1...N Array(max_len,Array(8,Bit))"""
    """Outputs: TX : BIT, run : BIT, ready : BIT"""
    name = _RegisterName('IOPrintf', n, init, ce, r, s)

    #XXX slightly wasteful, we compare against length instead of length - 1 so
    #we take 5 bits to represent a length of 16, for example.
    max_len = max(lengths)
    logn_max_len = log2(max_len)
    if ((1<<logn_max_len) <= max_len):
        logn_max_len = logn_max_len+1

    assert((1<<logn_max_len) > max_len)

    # need 2^N input MUX
    ceil_n = 1 << (log2((n - 1) * 2))

    IO = []
    #IO += ["length0", In(Array(logn_max_len,Bit))]
    for i in range(n):
        IO += ["valid%d" % i, In(Bit)]
        IO += ["data%d" % i, In(Array(lengths[i]*8,Bit))]

    #Control bits
    IO +=  ["ready", In(Bit)]
    IO +=  ["DTR", In(Bit)]

    #Outputs to I/O primitive
    IO += ["valid_out", Out(Bit), "data_out", Out(Array(8,Bit))] + ClockInterface(ce,r,s)

    @classmethod
    def definition(printf):
      #Convenience
      logn_max_len = printf.logn_max_len
      ceil_n       = printf.ceil_n
      baud = 1
      valid_idx = 0

      # Running is true while printing a message. It becomes false when we
      # finish the message and hit done.
      running = DFF(r=True)

      # print_cnt increments on running & the underlying I/O primitive's ready
      print_cnt = Counter(logn_max_len, ce=True, r=True)

      # We are done when print_cnt reaches the length of the message
      done = EQ(logn_max_len)
      if logn_max_len == 1:
        wire(print_cnt.O[0], done.I0)
      else:
        wire(print_cnt.O, done.I0)

      # Need to buffer the reset signal
      resetSignal = DFF()
      resetSignal(printf.RESET if r else 0)

      # We accept a message by latching the valid bits and the arguments
      # and transitioning to the running state
      printf_valid = array(*[getattr(printf,"valid%d"%i) for i in range(n)])
      any_valid = OrN(n)
      any_valid(printf_valid)
      should_accept = LUT2(~I0 & I1)(running, any_valid)

      running_n = LUT3((I0 & ~I1) | I2)(running, done, should_accept)
      running(running_n)
      #Reset running on RESET
      wire(resetSignal, running.RESET)

      #Running is true while we are printing real data, but turns to false if
      #we are stalling due to backpressure or have nothing to print
      #
      #We stay in the done state for many cycles if we are stalled due to
      #backpressure
      wire(running,printf.valid_out)

      # Latch valid
      valid_latch = Register(n,ce=True)
      valid_latch(printf_valid)
      wire(should_accept, valid_latch.CE)

      # Latch args
      # TODO latch the other args too!
      arg_latch = [
              RAM(
                      logn_max_len,
                      pad_garbage(getattr(printf,"data%d"%i),(1<<logn_max_len)*8),
                      print_cnt.O,
                      should_accept
              )
              for i in range(n)
              ]

      #### NOTE: Clean this up with python techniques & add support to 8 statements
      
      # Special handling for > 1 printf
      if n > 1:
        # Select winner among valid inputs (choose smallest valid index)
        if n == 2:
          val_idx = LUT2([0,0,1,0])
          val_idx(valid_latch.O[0], valid_latch.O[1])
        if n in [3, 4]:
          val_idx0 = LUT4([0,0,1,0,0,0,1,0,1,0,1,0,0,0,1,0])
          val_idx1 = LUT4([0,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0])
          val_idx0()
          val_idx1()
          for i in range(n):
            wire(valid_latch.O[i], getattr(val_idx0,"I%d"%i))
            wire(valid_latch.O[i], getattr(val_idx1,"I%d"%i))
          for i in range(ceil_n):
            if i >= n:
              wire(0, getattr(val_idx0,"I%d"%i))
              wire(0, getattr(val_idx1,"I%d"%i))
          val_idx  = array(val_idx1.O,val_idx0.O)

        # Select arguments to feed to UART based on valid index
        data_mux = Mux(ceil_n,8)
        len_mux  = Mux(ceil_n,logn_max_len)
        wire(val_idx, data_mux.S)
        wire(val_idx, len_mux.S)

        for i in range(n):
                wire(arg_latch[i], getattr(data_mux,"I%d"%i))
                wire(array(*int2seq(lengths[i], logn_max_len)), getattr(len_mux,"I%d"%i))
        # Connect the inputs to ground for unused MUX inputs
        for i in range(ceil_n):
          if i >= n:
            zeros = logn_max_len * [0]
            wire(array(*zeros), getattr(len_mux,"I%d"%i))
            zeros = 8 * [0]
            wire(array(*zeros), getattr(data_mux,"I%d"%i))
  
        # Wire data mux output to data_out
        wire(data_mux.O, printf.data_out)
        length = len_mux.O
      else:
        # Wire valid directly to latched valid and data directly to data_out
        wire(arg_latch[0], printf.data_out)
        length = array(*int2seq(lengths[0], logn_max_len))

      #Use length to determine "done"
      if logn_max_len == 1:
        wire(length[0], done.I1)
      else:
        wire(length, done.I1)

      #TODO we have to push some fake printfs through the pipeline sometimes.
      #Otherwise, the client will stall on a large buffer, and there is a
      #chance that as soon as it times out, we will be mid-printf and break a
      #buffer. To avoid this, periodically send a null message. To save
      #bandwidth, we need only send a null message when the number of sent
      #bytes is not a multiple of the buffer size.

      #If all printfs don't send the same amount, it is possible for a printf
      #to be split between two read buffers. That's OK, we just reconstitute
      #them on the CPU side.

      stream_has_more_space = 1

      #We can make the UART reliable, but it requires some cooperation with the
      #user program. Specifically, the user program must ACK every time it
      #reads a buffer from us, by rising-edge the DTR line
      if (reliable_uart_extension):
          BytesSent = Register(16, r=True, ce=True)
          BytesSent_n = Add(16)
          BytesSent_n(BytesSent, array(*int2seq(1, 16)))
          BytesSent(BytesSent_n.O)
          #Another byte is sent on every cycle where ready && running
          wire(LUT3((I0 & I1)|I2)(running, printf.ready, resetSignal),BytesSent.CE)
          wire(resetSignal, BytesSent.RESET)

          #Listen to ACKs via rising edge of DTR register.
          #Can't just compute rising edge as ~DTRbuffer & printf.DTR due to
          #glitches! The rising edge is only correctly detected if we buffer
          #again.
          DTRBuffer = DFF()
          DTRBuffer(printf.DTR)
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
                  array(*int2seq(bufferSize*2 - 1,16))
          )

          #Useful debugging:
          #wire(array(*[BytesInFlight.O[i] for i in range(8)]), printf.data_out)
          #wire(array(*[BytesSent.O[i] for i in range(8)]), printf.data_out)

      reset = LUT3((I0 & I1) | I2)
      reset(done, stream_has_more_space, resetSignal)
      wire(reset, print_cnt.RESET)

      #TODO
      #Advance on ready, unless done, or reset
      wire(LUT3((I0 & I1)|I2)(running, printf.ready, reset), print_cnt.CE)
  return _IOPrintf

def IOPrintf(lengths, ce=False, r=False, s=False, **kwargs):
    return DefineIOPrintf(lengths, ce, r, s)(**kwargs)
