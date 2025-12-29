import ctypes
import os
import socket

_libname = "scpi_client.dll"
_libpath = os.path.join(os.path.dirname(__file__), "..", "c_scpi", _libname)

_scpi = ctypes.CDLL(_libpath)

_scpi.scpi_connect.argtypes = [ctypes.c_char_p, ctypes.c_int]
_scpi.scpi_connect.restype = ctypes.c_int

_scpi.scpi_write.argtypes = [ctypes.c_int, ctypes.c_char_p]
_scpi.scpi_write.restype = ctypes.c_int

_scpi.scpi_query.argtypes = [
    ctypes.c_int,
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_int,
]
_scpi.scpi_query.restype = ctypes.c_int

_scpi.scpi_close.argtypes = [ctypes.c_int]
_scpi.scpi_close.restype = None


class ScpiCClient:
    def __init__(self, host, port):
        self.sock = _scpi.scpi_connect(host.encode(), port)

    def write(self, cmd):
        _scpi.scpi_write(self.sock, cmd.encode())

    def query(self, cmd):
        buf = ctypes.create_string_buffer(8192)
        _scpi.scpi_query(self.sock, cmd.encode(), buf, len(buf))
        return buf.value.decode().strip()

    def close(self):
        _scpi.scpi_close(self.sock)
