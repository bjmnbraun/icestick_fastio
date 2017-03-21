from printf import *

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

def fastio_printf(condition, format_string, *argv):
        return PrintIO(iospec_file, condition, format_string, *argv)

def fastio_compile_hook():
        global connection
        return PrintIOConn(
                "UART",
                ce=False,
                r=True,
                s=False
        )(
                RESET=connection['RESET'],
                DTR=connection['DTR'],
                TX=connection['TX']
        )
