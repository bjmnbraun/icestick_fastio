import sys
import json
import iocc_emitter
from splitstream import splitfile
from enum import Enum

class IOModes(Enum):
        UNKNOWN = 1
        PRINTF = 2
        DISPLAY = 3
        #More to come?

#Parsing state:
current_mode = IOModes.UNKNOWN
connections = {}
io_elements = []

def parse_connection(connection):
        global connections
        if (len(connections)):
                raise ValueError("Multiple connections not supported")
        connection_id = connection['id']
        connections[connection_id] = connection
        #print(connections)

def parse_io_element(element):
        global current_mode
        global io_elements
        if (iospec['type'] == "printf"):
                element_mode = IOModes.PRINTF
        else:
                raise ValueError
        if element_mode == current_mode or current_mode == IOModes.UNKNOWN:
                current_mode = element_mode
        else:
                raise ValueError("Can't currently mix modes!")
        io_elements += [element]
        #print(io_elements)

#Main loop
iocc_emitter.init(sys.argv[1], sys.argv[3])

#XXX
parse_connection({'id':0})

try:
        with open(sys.argv[2], 'r') as iospec_f:
                for jsonstr in splitfile(iospec_f, format="json"):
                        iospec = json.loads(jsonstr)
                        if (iospec['type'] == "connection"):
                                parse_connection(iospec)
                        elif (iospec['type'] == "printf"):
                                parse_io_element(iospec)
                        else:
                                raise ValueError
except FileNotFoundError as e:
        print("No iospec file generated, building dummy binary")
        current_mode = IOModes.PRINTF

#TODO support for multiple connections
if (current_mode == IOModes.PRINTF):
        iocc_emitter.emit_printf(
                list(connections.values())[0],
                io_elements
        )
else:
        raise ValueError
