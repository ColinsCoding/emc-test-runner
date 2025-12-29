from core.scpi_ctypes import ScpiCClient


class InstrumentC:
    def __init__(self, host, port=5025):
        self.client = ScpiCClient(host, port)

    def idn(self):
        return self.client.query("*IDN?")

    def configure_sweep(self, start, stop, points):
        self.client.write(f"FREQ:START {start}")
        self.client.write(f"FREQ:STOP {stop}")
        self.client.write(f"SWE:POIN {points}")

    def acquire_trace(self):
        self.client.write("INIT")
        data = self.client.query("TRAC?")
        return [float(x) for x in data.split(",")]

    def close(self):
        self.client.close()
