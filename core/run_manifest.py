# core/run_manifest.py
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def make_run_dir(base: str = "runs") -> str:
    os.makedirs(base, exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(base, run_id)
    os.makedirs(path, exist_ok=True)
    return path


@dataclass
class RunManifest:
    run_id: str
    start_time: str
    end_time: str | None
    status: str
    error: str | None

    host: str
    port: int
    idn: str | None

    sweep_start_hz: float
    sweep_stop_hz: float
    sweep_points: int

    trace_csv: str
    transcript: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    def write(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_json())
            f.write("\n")
