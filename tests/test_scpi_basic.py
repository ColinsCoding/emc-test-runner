import unittest
import statistics

from core.instrument import Instrument

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


class TestScpiBasic(unittest.TestCase):
    def test_trace_length_and_peaks(self):
        inst = Instrument(HOST, PORT)
        try:
            inst.connect()

            idn = inst.idn()
            self.assertIn("HPE", idn)

            inst.set_sweep(START_HZ, STOP_HZ, POINTS)
            trace = inst.get_trace()

            self.assertEqual(len(trace), POINTS)

            peak_count = count_local_peaks(trace, min_prominence=6.0)
            self.assertGreaterEqual(peak_count, 2)

        finally:
            inst.close()


def smoke() -> None:
    """
    Day-1 checklist smoke test:
      - start simulator manually in another terminal
      - connect
      - print IDN
      - set sweep
      - fetch trace
      - assert length == points
      - print 'trace points OK'
    """
    print("NOTE: Start the simulator in another terminal:")
    print("  python .\\sim\\scpi_sim.py\n")

    inst = Instrument(HOST, PORT)
    inst.connect()

    idn = inst.idn()
    print(f"IDN: {idn}")

    inst.set_sweep(START_HZ, STOP_HZ, POINTS)
    trace = inst.get_trace()

    assert len(trace) == POINTS, f"Trace length {len(trace)} != {POINTS}"
    print("trace points OK")

    inst.close()


if __name__ == "__main__":
    # Running as a script -> prints the exact lines you need to screenshot
    smoke()
