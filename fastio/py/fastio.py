from fastio_common import *
from fastio_internal import \
        fastio_setup, \
        fastio_printf, \
        fastio_simple_display, \
        fastio_compile_hook

#Convenient alias for fastio_printf
def printf(condition, format_string, *args):
    return fastio_printf(condition, format_string, *args)
