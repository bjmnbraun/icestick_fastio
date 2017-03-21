import sys
import json
import iocc_emitter
from splitstream import splitfile
from enum import Enum

iocc_emitter.init(sys.argv[1])
iospec_f = open(sys.argv[2], 'r')
out_prefix = open(sys.argv[3] + "-io.c", 'w')

class IOModes(Enum):
        UNKNOWN = 1
        PRINTF = 2
        DISPLAY = 3
        #More to come?

#Parsing state:
current_mode = IOModes.UNKNOWN
connections = {}

def parse_connection(connection):
        global connections
        connection_id = connection['id']
        connections[connection_id] = connection
        print(connections)

def parse_printf(printf):
        global current_mode
        if (current_mode == IOModes.UNKNOWN):
                current_mode = IOModes.PRINTF
                iocc_emitter.emit_printf_header()
        elif (current_mode == IOModes.PRINTF):
                pass
        else:
                raise ValueError("Can't mix IOs yet!")

        iocc_emitter.emit_printf(printf)

for jsonstr in splitfile(iospec_f, format="json"):
        iospec = json.loads(jsonstr)
        if (iospec['type'] == "connection"):
                parse_connection(iospec)
        elif (iospec['type'] == "printf"):
                parse_printf(iospec)
        else:
                raise ValueError
