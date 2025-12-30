# run_scpi_sweep.py
import argparse
import os
from core.run_manifest import RunManifest, make_run_dir, now_iso
from core.scpi_logger import ScpiLogger


def parse_trace_csv_line(line: str) -> list[float]:
    # line is comma-separated amplitudes
    parts = [p for p in line.split(",") if p]
    return [float(p) for p in parts]


def write_trace_csv(path: str, amps: list[float]) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("index,amplitude_dbm\n")
        for i, a in enumerate(amps):
            f.write(f"{i},{a:.2f}\n")


def run_once(host: str, port: int, start_hz: float, stop_hz: float, points: int, run_dir: str):
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

        # Simulated timeouts come back as ERROR:SIM_TIMEOUT
        if trace_line.startswith("ERROR:"):
            raise TimeoutError(trace_line)

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

    last_err = None
    for attempt in (1, 2):  # retry once
        try:
            m = run_once(args.host, args.port, args.start_hz, args.stop_hz, args.points, run_dir)
            m.end_time = now_iso()
            m.write(manifest_path)
            print(f"Run dir: {run_dir}")
            print(f"IDN: {m.idn}")
            print("status: PASS")
            return
        except Exception as e:
            last_err = e
            # retry once on ERROR: or connection drop; we treat any exception as retryable for Day 2
            if attempt == 1:
                continue
            # fail after retry
            from core.run_manifest import RunManifest  # avoid circular import in some setups
            # Read existing manifest fields by regenerating minimal finalization
            # (We overwrite the manifest with status+end_time+error)
            # Best practice: keep the same run_dir for traceability.
            # NOTE: if you want, we can refactor to load existing json.
            pass

    # finalize failure manifest
    # (recreate same manifest structure; safer than partial edits)
    m_fail = RunManifest(
        run_id=os.path.basename(run_dir),
        start_time="",
        end_time=now_iso(),
        status="FAIL",
        error=str(last_err),
        host=args.host,
        port=args.port,
        idn=None,
        sweep_start_hz=args.start_hz,
        sweep_stop_hz=args.stop_hz,
        sweep_points=args.points,
        trace_csv="trace.csv",
        transcript="scpi_transcript.log",
    )
    m_fail.write(manifest_path)
    print(f"Run dir: {run_dir}")
    print(f"status: FAIL ({last_err})")


if __name__ == "__main__":
    main()
