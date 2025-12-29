from datetime import datetime
from pathlib import Path


class ScpiLogger:
    def __init__(self, run_dir):
        self.log_path = Path(run_dir) / "scpi_session.log"

    def log_tx(self, cmd):
        self._write("TX", cmd)

    def log_rx(self, resp):
        self._write("RX", resp)

    def _write(self, tag, msg):
        with open(self.log_path, "a") as f:
            f.write(f"{datetime.utcnow().isoformat()} {tag}: {msg}\n")
