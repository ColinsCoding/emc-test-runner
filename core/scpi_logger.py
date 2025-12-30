# core/scpi_logger.py
import os
import ctypes
from ctypes import c_char_p, c_int, create_string_buffer
from dataclasses import dataclass
from datetime import datetime


def _default_lib_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.abspath(os.path.join(here, ".."))
    cdir = os.path.join(repo, "c_scpi")
    if os.name == "nt":
        return os.path.join(cdir, "scpi_client.dll")
    return os.path.join(cdir, "libscpi_client.so")


def _ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class ScpiLogger:
    """
    C-backed SCPI client with transcript logging.
    - write(): logs TX only
    - query(): logs TX and RX (one line)
    """
    host: str
    port: int
    transcript_path: str
    lib_path: str | None = None
    out_sz: int = 1024 * 1024

    def __post_init__(self) -> None:
        self.sock = -1
        self._fh = open(self.transcript_path, "a", encoding="utf-8", newline="\n")

        path = self.lib_path or _default_lib_path()
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
        self._log(f"CONNECT {self.host}:{self.port}")

    def close(self) -> None:
        if self.sock != -1:
            try:
                self.lib.scpi_close(self.sock)
            finally:
                self._log("CLOSE")
                self.sock = -1
        try:
            self._fh.close()
        except Exception:
            pass

    def _log(self, line: str) -> None:
        self._fh.write(f"{_ts()} {line}\n")
        self._fh.flush()

    def write(self, cmd: str) -> None:
        self._log(f"TX {cmd}")
        rc = self.lib.scpi_write(self.sock, cmd.encode("utf-8"))
        if rc != 0:
            self._log("ERR write_failed")
            raise ConnectionError("SCPI write failed (socket dropped?)")

    def query(self, cmd: str) -> str:
        self._log(f"TX {cmd}")
        buf = create_string_buffer(self.out_sz)
        rc = self.lib.scpi_query(self.sock, cmd.encode("utf-8"), buf, self.out_sz)
        if rc != 0:
            self._log("ERR query_failed")
            raise ConnectionError("SCPI query failed (socket dropped?)")

        rx = buf.value.decode("utf-8", errors="replace").strip()
        self._log(f"RX {rx}")
        return rx
