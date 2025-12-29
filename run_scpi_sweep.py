import argparse
from pathlib import Path
from datetime import datetime

from core.instrument_c import InstrumentC
from core.run_manifest import write_manifest


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", required=True)
    p.add_argument("--start", type=float, required=True)
    p.add_argument("--stop", type=float, required=True)
    p.add_argument("--points", type=int, default=1001)
    args = p.parse_args()

    run_dir = Path("runs") / datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    run_dir.mkdir(parents=True)

    inst = InstrumentC(args.host)
    idn = inst.idn()

    inst.configure_sweep(args.start, args.stop, args.points)
    trace = inst.acquire_trace()

    with open(run_dir / "results.csv", "w") as f:
        for v in trace:
            f.write(f"{v}\n")

    write_manifest(run_dir, idn, vars(args))
    inst.close()


if __name__ == "__main__":
    main()
