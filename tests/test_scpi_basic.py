import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import statistics

BACKEND = os.environ.get("SCPI_BACKEND", "py").lower()

if BACKEND == "c":
    from core.instrument_c import InstrumentC as Instrument
elif BACKEND == "py":
    from core.instrument import Instrument
else:
    raise RuntimeError(f"Unknown SCPI_BACKEND={BACKEND!r}")


# -------- Test configuration --------

HOST = "127.0.0.1"
PORT = 5025

START_HZ = 30e6
STOP_HZ = 1e9
POINTS = 1001


def count_local_peaks(y: list[float], min_prominence: float) -> int:
    if len(y) < 3:
        return 0
    baseline = statistics.median(y)
    c = 0
    for i in range(1, len(y) - 1):
        if y[i - 1] < y[i] > y[i + 1] and (y[i] - baseline) >= min_prominence:
            c += 1
    return c


def main() -> None:
    print(f"SCPI_BACKEND = {BACKEND}")
    print("NOTE: Simulator must already be running.\n")

    inst = Instrument(HOST, PORT)
    inst.connect()

    idn = inst.idn()
    print(f"IDN: {idn}")

    inst.set_sweep(START_HZ, STOP_HZ, POINTS)
    trace = inst.get_trace()

    assert len(trace) == POINTS, f"Trace length {len(trace)} != {POINTS}"

    peak_count = count_local_peaks(trace, min_prominence=6.0)
    assert peak_count >= 2, f"Expected >=2 peaks, got {peak_count}"

    print("trace points OK")
    print("peaks detected OK")

    inst.close()


if __name__ == "__main__":
    main()
