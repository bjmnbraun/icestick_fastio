from printf import *

from display import *

import uart

from fastio_common import *

iospec_prefix = None
iospec_file = None
connection = None
def fastio_setup(connection_type, _iospec_prefix, RESET, DTR, TX):
        global connection
        global iospec_prefix
        global iospec_file
        if (connection):
                raise ValueError("Please call fastio_setup once")
        if (connection_type != UART):
                raise ValueError("Only UART is currently supported")
        iospec_prefix = _iospec_prefix
        iospec_file = open(iospec_prefix + ".iospec.json", "w")
        connection = {
                'connection_type':connection_type,
                'RESET':RESET,
                'DTR':DTR,
                'TX':TX
        }
        print(connection)

FASTIO_MODE_PRINTF = 1
FASTIO_MODE_DISPLAY = 2

mode = None
def fastio_printf(condition, format_string, *argv):
        global mode
        if (mode and mode != FASTIO_MODE_PRINTF):
                raise ValueError("Can't mix I/O modes yet")
        mode = FASTIO_MODE_PRINTF
        return PrintIO(iospec_file, condition, format_string, *argv)

def fastio_simple_display(width, height, bpp):
        global mode
        global connection
        if (mode and mode != FASTIO_MODE_DISPLAY):
                raise ValueError("Can't mix I/O modes yet")
        if (mode == FASTIO_MODE_DISPLAY):
                raise ValueError("Multiple displays not yet implemented")
        mode = FASTIO_MODE_DISPLAY

        display = DisplayConn(
                iospec_file, "UART", width, height, bpp
        )
        wire(connection['RESET'], display.RESET)
        wire(connection['DTR'], display.DTR)
        wire(connection['TX'], display.TX)
        return display

def fastio_compile_hook():
        global mode
        global connection
        if (mode == FASTIO_MODE_PRINTF):
                PrintIOConn(
                        "UART",
                        ce=False,
                        r=True,
                        s=False
                )(
                        RESET=connection['RESET'],
                        DTR=connection['DTR'],
                        TX=connection['TX']
                )
