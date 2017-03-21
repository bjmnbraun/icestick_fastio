from printf import *

from fastio_common import *

connection = None
def fastio_setup(connection_type, iospec_prefix, RESET, DTR, TX):
        global connection
        if (connection):
                raise ValueError("Please call fastio_setup once")
        if (connection_type != UART):
                raise ValueError("Only UART is currently supported")
        connection = {
                'connection_type':connection_type,
                'iospec_prefix':iospec_prefix,
                'RESET':RESET,
                'DTR':DTR,
                'TX':TX
        }
        print(connection)

def fastio_printf(condition, format_string, *argv):
        return PrintIO(condition, format_string, *argv)

def fastio_compile_hook():
        global connection
        return PrintIOConn(
                "UART",
                ce=False,
                r=True,
                s=False
        )(
                RESET=connection['RESET'],
                dtr=connection['DTR'],
                TX=connection['TX']
        )
