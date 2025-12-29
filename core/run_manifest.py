import json
import subprocess
from datetime import datetime
from pathlib import Path


def write_manifest(run_dir, instrument_idn, config):
    manifest = {
        "timestamp": datetime.utcnow().isoformat(),
        "instrument_idn": instrument_idn,
        "config": config,
        "git_commit": _git_commit(),
    }

    path = Path(run_dir) / "run_manifest.json"
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)


def _git_commit():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "unknown"
