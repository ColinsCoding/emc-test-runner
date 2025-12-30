import os
import ctypes
from ctypes import c_char_p, c_int, create_string_buffer


def _lib_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.abspath(os.path.join(here, ".."))
    cdir = os.path.join(repo, "c_scpi")

    if os.name == "nt":
        return os.path.join(cdir, "scpi_client.dll")

    for name in ("libscpi_client.so", "libscpi_client.dylib"):
        p = os.path.join(cdir, name)
        if os.path.exists(p):
            return p
    return os.path.join(cdir, "libscpi_client.so")


class InstrumentC:
    """
    C/ctypes SCPI backend.
    API matches tests: connect(), idn(), set_sweep(), get_trace(), close()
    """
    def __init__(self, host: str = "127.0.0.1", port: int = 5025):
        self.host = host
        self.port = port
        self.sock = -1

        path = _lib_path()
        if not os.path.exists(path):
            raise FileNotFoundError(f"SCPI client library not found: {path}")

        self.lib = ctypes.CDLL(path)

        self.lib.scpi_connect.argtypes = [c_char_p, c_int]
        self.lib.scpi_connect.restype = c_int

        self.lib.scpi_write.argtypes = [c_int, c_char_p]
        self.lib.scpi_write.restype = c_int

        self.lib.scpi_query.argtypes = [c_int, c_char_p, ctypes.c_char_p, c_int]
        self.lib.scpi_query.restype = c_int

        self.lib.scpi_close.argtypes = [c_int]
        self.lib.scpi_close.restype = None

    def connect(self) -> None:
        if self.sock != -1:
            return
        s = self.lib.scpi_connect(self.host.encode("utf-8"), int(self.port))
        if s < 0:
            raise ConnectionError(f"Failed to connect to {self.host}:{self.port}")
        self.sock = int(s)

    def close(self) -> None:
        if self.sock != -1:
            self.lib.scpi_close(self.sock)
            self.sock = -1

    def _write(self, cmd: str) -> None:
        rc = self.lib.scpi_write(self.sock, cmd.encode("utf-8"))
        if rc != 0:
            raise ConnectionError("SCPI write failed (socket dropped?)")

    def _query_line(self, cmd: str, out_sz: int = 1024 * 1024) -> str:
        buf = create_string_buffer(out_sz)
        rc = self.lib.scpi_query(self.sock, cmd.encode("utf-8"), buf, out_sz)
        if rc != 0:
            raise ConnectionError("SCPI query failed (socket dropped?)")
        return buf.value.decode("utf-8", errors="replace").strip()

    def idn(self) -> str:
        return self._query_line("*IDN?")

    def set_sweep(self, start_hz: float, stop_hz: float, points: int) -> None:
        self._write(f"FREQ:STAR {start_hz}")
        self._write(f"FREQ:STOP {stop_hz}")
        self._write(f"SWE:POIN {points}")

    def get_trace(self) -> list[float]:
        self._write("INIT:IMM")
        line = self._query_line("TRAC?")
        if line.startswith("ERROR:"):
            raise RuntimeError(line)
        return [float(x) for x in line.split(",") if x]
