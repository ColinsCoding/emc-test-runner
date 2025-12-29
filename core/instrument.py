import os
import ctypes
from ctypes import c_char_p, c_int, create_string_buffer


def _lib_path() -> str:
    # Load from repo-relative path: c_scpi/scpi_client.dll on Windows
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.abspath(os.path.join(here, ".."))
    cdir = os.path.join(repo, "c_scpi")

    if os.name == "nt":
        return os.path.join(cdir, "scpi_client.dll")
    # (If you later build on Linux/mac)
    # Linux: libscpi_client.so, mac: libscpi_client.dylib (or .so)
    for name in ("libscpi_client.so", "libscpi_client.dylib", "scpi_client.so"):
        cand = os.path.join(cdir, name)
        if os.path.exists(cand):
            return cand
    return os.path.join(cdir, "libscpi_client.so")


class Instrument:
    """
    C-backed SCPI-over-TCP instrument client (LAN).
    Exposes: connect(), idn(), set_sweep(), get_trace(), close()
    """
    def __init__(self, host: str = "127.0.0.1", port: int = 5025):
        self.host = host
        self.port = port
        self.sock = -1

        path = _lib_path()
        if not os.path.exists(path):
            raise FileNotFoundError(f"SCPI client library not found: {path}")

        self.lib = ctypes.CDLL(path)

        # int scpi_connect(const char* host, int port);
        self.lib.scpi_connect.argtypes = [c_char_p, c_int]
        self.lib.scpi_connect.restype = c_int

        # int scpi_write(int sock, const char* cmd);
        self.lib.scpi_write.argtypes = [c_int, c_char_p]
        self.lib.scpi_write.restype = c_int

        # int scpi_query(int sock, const char* cmd, char* out, int out_sz);
        self.lib.scpi_query.argtypes = [c_int, c_char_p, ctypes.c_char_p, c_int]
        self.lib.scpi_query.restype = c_int

        # void scpi_close(int sock);
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
            raise OSError(f"scpi_write failed for: {cmd!r}")

    def _query_line(self, cmd: str, out_sz: int = 1024 * 1024) -> str:
        buf = create_string_buffer(out_sz)
        rc = self.lib.scpi_query(self.sock, cmd.encode("utf-8"), buf, out_sz)
        if rc != 0:
            raise OSError(f"scpi_query failed for: {cmd!r}")
        # Strip trailing newline from returned line
        return buf.value.decode("utf-8", errors="replace").strip()

    # Public API required by your checklist
    def idn(self) -> str:
        return self._query_line("*IDN?")

    def set_sweep(self, start_hz: float, stop_hz: float, points: int) -> None:
        # setters are typically silent; your simulator should be silent too
        self._write(f"FREQ:STAR {start_hz}")
        self._write(f"FREQ:STOP {stop_hz}")
        self._write(f"SWE:POIN {points}")

    def get_trace(self) -> list[float]:
        # arm measurement, then get trace
        self._write("INIT:IMM")
        s = self._query_line("TRAC?")
        parts = s.split(",")
        try:
            return [float(x) for x in parts if x]
        except ValueError as e:
            raise ValueError(f"TRAC? returned non-numeric response: {s!r}") from e
