# run_scpi_sweep.py
import argparse
import os

from core.run_manifest import RunManifest, make_run_dir, now_iso
from core.scpi_logger import ScpiLogger


def parse_trace_csv_line(line: str) -> list[float]:
    parts = [p for p in line.split(",") if p]
    return [float(p) for p in parts]


def write_trace_csv(path: str, amps: list[float]) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("index,amplitude_dbm\n")
        for i, a in enumerate(amps):
            f.write(f"{i},{a:.2f}\n")


def is_retryable_error(e: Exception) -> bool:
    """
    Retry once on:
      - simulator injected query errors: "ERROR:..."
      - dropped connections / transport issues
    """
    msg = str(e)
    if msg.startswith("ERROR:"):
        return True
    low = msg.lower()
    return any(k in low for k in ("dropped", "drop", "reset", "aborted", "broken pipe", "failed to connect", "query failed", "write failed"))


def run_once(host: str, port: int, start_hz: float, stop_hz: float, points: int, run_dir: str) -> RunManifest:
    transcript_path = os.path.join(run_dir, "scpi_transcript.log")
    csv_path = os.path.join(run_dir, "trace.csv")
    manifest_path = os.path.join(run_dir, "manifest.json")

    manifest = RunManifest(
        run_id=os.path.basename(run_dir),
        start_time=now_iso(),
        end_time=None,
        status="RUNNING",
        error=None,
        host=host,
        port=port,
        idn=None,
        sweep_start_hz=start_hz,
        sweep_stop_hz=stop_hz,
        sweep_points=points,
        trace_csv="trace.csv",
        transcript="scpi_transcript.log",
    )
    manifest.write(manifest_path)

    scpi = ScpiLogger(host, port, transcript_path)
    try:
        scpi.connect()

        idn = scpi.query("*IDN?")
        manifest.idn = idn

        # Set sweep (setters should be silent on your simulator)
        scpi.write(f"FREQ:STAR {start_hz}")
        scpi.write(f"FREQ:STOP {stop_hz}")
        scpi.write(f"SWE:POIN {points}")

        # Arm + fetch trace
        scpi.write("INIT:IMM")
        trace_line = scpi.query("TRAC?")

        # Simulator injected errors
        if trace_line.startswith("ERROR:"):
            # Raise with message that starts with ERROR: so retry logic triggers
            raise RuntimeError(trace_line)

        amps = parse_trace_csv_line(trace_line)
        if len(amps) != points:
            raise ValueError(f"Trace length {len(amps)} != {points}")

        write_trace_csv(csv_path, amps)

        manifest.status = "PASS"
        return manifest

    finally:
        try:
            scpi.close()
        except Exception:
            pass


def main() -> None:
    ap = argparse.ArgumentParser(description="Run a SCPI sweep and save run artifacts")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5025)
    ap.add_argument("--start-hz", type=float, default=30e6)
    ap.add_argument("--stop-hz", type=float, default=1e9)
    ap.add_argument("--points", type=int, default=1001)
    args = ap.parse_args()

    run_dir = make_run_dir("runs")
    manifest_path = os.path.join(run_dir, "manifest.json")

    manifest: RunManifest | None = None
    last_err: Exception | None = None

    for attempt in (1, 2):  # retry once
        try:
            manifest = run_once(args.host, args.port, args.start_hz, args.stop_hz, args.points, run_dir)
            manifest.end_time = now_iso()
            manifest.error = None
            manifest.write(manifest_path)

            print(f"Run dir: {run_dir}")
            print(f"IDN: {manifest.idn}")
            print("status: PASS")
            return

        except Exception as e:
            last_err = e

            # retry once only if retryable
            if attempt == 1 and is_retryable_error(e):
                continue

            # finalize FAIL (ensure we have a manifest object)
            if manifest is None:
                manifest = RunManifest(
                    run_id=os.path.basename(run_dir),
                    start_time=now_iso(),
                    end_time=None,
                    status="RUNNING",
                    error=None,
                    host=args.host,
                    port=args.port,
                    idn=None,
                    sweep_start_hz=args.start_hz,
                    sweep_stop_hz=args.stop_hz,
                    sweep_points=args.points,
                    trace_csv="trace.csv",
                    transcript="scpi_transcript.log",
                )

            manifest.status = "FAIL"
            manifest.end_time = now_iso()
            manifest.error = str(last_err)
            manifest.write(manifest_path)

            print(f"Run dir: {run_dir}")
            print(f"status: FAIL ({last_err})")
            return


if __name__ == "__main__":
    main()
