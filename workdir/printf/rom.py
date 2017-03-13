from magma import *
from mantle import *

def REGs(n,init=0,ce=True):
    return [Register(8,init=init,ce=True) for i in range(n)]

def MUXs(n):
    return [Mux(2,8) for i in range(n)]

def RAM(logn, init, A, ce=True):
    n = 1 << logn
    assert len(A) == logn

    #TODO pad init with garbled characters or?
    assert len(init) == n

    #data in
    regs = REGs(n,ce=ce)
    for i in range(n):
        regs[i](init[i], CE=ce)

    muxs = MUXs(n-1)
    for i in range(n/2):
        muxs[i](regs[2*i], regs[2*i+1], A[0])

    k = 0
    l = 1 << (logn-1)
    for i in range(logn-1):
        for j in range(l/2):
            muxs[k+l+j](muxs[k+2*j], muxs[k+2*j+1], A[i+1])
        k += l
        l /= 2

    return muxs[n-2]

def ROM(logn, init, A):
    n = 1 << logn
    assert len(A) == logn

    #TODO pad init with garbled characters or?
    assert len(init) == n

    muxs = MUXs(n-1)
    for i in range(n/2):
        muxs[i](init[2*i], init[2*i+1], A[0])

    k = 0
    l = 1 << (logn-1)
    for i in range(logn-1):
        for j in range(l/2):
            muxs[k+l+j](muxs[k+2*j], muxs[k+2*j+1], A[i+1])
        k += l
        l /= 2

    return muxs[n-2]

