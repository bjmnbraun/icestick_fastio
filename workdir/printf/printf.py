import sys
from magma import *
from mantle import *
from rom import ROM
from rom import RAM
from mantle.lattice.mantle40.MUX import Mux4
from mantle.lattice.mantle40.register import _RegisterName, Register
from boards.icestick import IceStick

def REGs(n):
    return [Register(8, ce=True) for i in range(n)]

def DefineIOPrintf (n, init=0, ce=False, r=False, s=False):

  class _IOPrintf(Circuit):
    assert n in [1, 2, 4]
    """Construct a printf IO type"""
    """Inputs:  valid : Array(n,Bit), length : Array(n,Array(4,Bit)),
      arg1...N Array(max_len,Array(8,Bit))"""
    """Outputs: TX : BIT, run : BIT, ready : BIT"""
    name = _RegisterName('IOPrintf', n, init, ce, r, s)
    
    # Limit argument length + header to 4 bytes for now
    logn_max_len = 2
    #max_len      = 1<<logn_max_len
    
    IO =  ["valid", In(Array(n,Bit))]
    IO += ["length0", In(Array(logn_max_len,Bit))]
    #IO += ["data0", In(Array(1<<logn_max_len,Array(8,Bit)))]
    IO += ["data0_arg0", In(Array(8,Bit)), "data0_arg1", In(Array(8,Bit)), "data0_arg2", In(Array(8,Bit)), "data0_arg3", In(Array(8,Bit))]
    if n > 1:
      IO += ["data1", In(Array(1<<logn_max_len,Array(8,Bit)))]
    if n > 2:
      IO += ["data2", In(Array(1<<logn_max_len,Array(8,Bit)))]
    if n > 3:
      IO += ["data3", In(Array(1<<logn_max_len,Array(8,Bit)))]
    IO +=  ["ready", In(Bit)]
    IO += ["valid_out", Out(Bit), "data_out", Out(Array(8,Bit))] + ClockInterface(ce,r,s)

    @classmethod
    def definition(printf):

      logn_max_len = 2
      baud = 1
      logn = 2
      done = 1
      valid_idx = 0
      
      # print over length of arguments
      print_cnt = Counter(logn, ce=True, r=True)

      ### Latch input arguments when printf is idle
      
      # Latch valid    
      valid_latch = Register(n,ce=True)
      valid_latch()
      wire(printf.valid, valid_latch)
      wire(done, valid_latch.CE)
      
      # Latch args
      arg_latch0 = RAM(logn_max_len,array(printf.data0_arg0, printf.data0_arg1, printf.data0_arg2, printf.data0_arg3), print_cnt.O)
      #arg_latch0(CE=done)
      if n > 1:
        arg_latch1 = RAM(logn_max_len,printf.data1, print_cnt.O)
        arg_latch1(CE=done)
      if n > 2:
        arg_latch2 = RAM(logn_max_len,printf.data2, print_cnt.O)
        arg_latch2(CE=done)
        arg_latch3 = RAM(logn_max_len,printf.data3, print_cnt.O)
        arg_latch3(CE=done)

      # Special handling for > 1 printf
      if n > 1:
        # Select winner among valid inputs (choose smallest valid index)
        any_valid = OrN(n)
        wire(valid_latch.O[0], any_valid.I[0])
        wire(valid_latch.O[1], any_valid.I[1])
        if n == 2:
          val_idx = LUT2[0,0,1,0]
          val_idx(valid[0],valid[1])
        if n == 4:
          val_idx0 = LUT4[0,0,1,0,0,0,1,0,1,0,1,0,0,0,1,0]
          val_idx1 = LUT4[0,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0]
          val_idx  = array(val_idx1,val_idx0)
          wire(valid_latch.O[2], any_valid.I[2])
          wire(valid_latch.O[3], any_valid.I[3])
          
        # Select arguments to feed to UART based on valid index
        data_mux = Mux(n,8)
        len_mux  = Mux(n,logn_max_len)
        wire(val_idx, data_mux.S)
        wire(val_idx, len_mux.S)
        
        wire(arg_latch0.O, data_mux.I0)
        wire(arg_latch1.O, data_mux.I1)
        wire(printf.length0, len_mux.I0)
        wire(printf.length1, len_mux.I1)
        if n > 2:
          wire(arg_latch2.O, data_mux.I2)
          wire(arg_latch3.O, data_mux.I3)
          wire(printf.length[2], len_mux.I2)
          wire(printf.length[3], len_mux.I3)

        # Wire data mux output to data_out
        wire(data_mux.O, printf.data_out)
      else:
        # Just 1 printf defined
        len_mux  = Mux(2,logn_max_len)
        wire(printf.length0, len_mux.I0)
        wire(printf.length0, len_mux.I1)
        wire(0, len_mux.S)
        
        # Wire valid directly to latched valid and data directly to data_out
        any_valid = OrN(2)
        wire(valid_latch.O[0], any_valid.I[0])
        wire(valid_latch.O[0], any_valid.I[1])
        wire(arg_latch0.O, printf.data_out)
        
      # Wire 0 or selected length to done comparitor based on any_valid
      done_mux = Mux(2,logn_max_len)
      wire(array(0,0),done_mux.I0)
      wire(len_mux.O, done_mux.I1)
      wire(any_valid.O, done_mux.S)
      
      # Counter runs when ~done && UART is ready for data
      done_logic = NE(logn_max_len)
      done_logic(print_cnt.O,done_mux.O)
      busy = OrN(2)
      wire(done_logic.O, busy.I[0])
      wire(any_valid.O, busy.I[1])
      wire(busy.O,printf.valid_out)
      
      # Stall and reset counter based in inputs
      ready = LUT2(I0&I1)
      ready(printf.ready, done_logic.O)
      wire(ready, print_cnt.CE)
      
      # Start circuit - detect any_valid && done transition
      new_data = LUT2(I0&I1)
      new_data(any_valid.O, done_logic.O)
      new_dff = DFF()
      new_dff(new_data)
      new_data_inv = LUT1(~I0)
      new_data_inv(new_data)
      start = AndN(2)
      wire(new_data_inv.O, start.I[0])
      wire(new_dff.O, start.I[1])

      wire(start.O, print_cnt.RESET)
  return _IOPrintf

def IOPrintf(n, init=0, ce=False, r=False, s=False, **kwargs):
    return DefineIOPrintf(n, init, ce, r, s)(**kwargs)

