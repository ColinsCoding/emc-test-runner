import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# Reuse your run dir / manifest logic
from core.run_manifest import RunManifest, make_run_dir, now_iso
from run_scpi_sweep import write_trace_csv  # uses your existing CSV writer

from core.instrument import Instrument


def load_instrument(backend: str):
    backend = backend.lower()
    if backend == "py":
        from core.instrument import Instrument
        return Instrument
    if backend == "c":
        from core.instrument_c import InstrumentC
        return InstrumentC
    raise ValueError(f"Unknown backend: {backend}")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("EMC Test Runner (Day 2 GUI)")
        self.geometry("950x650")

        self.inst = None
        self.connected = False
        self.stop_requested = False
        self.worker = None

        # ---- Top control panel ----
        frm = ttk.Frame(self, padding=10)
        frm.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(frm, text="Backend:").grid(row=0, column=0, sticky="w")
        self.backend_var = tk.StringVar(value=os.environ.get("SCPI_BACKEND", "py"))
        ttk.Combobox(frm, textvariable=self.backend_var, values=["py", "c"], width=5, state="readonly").grid(row=0, column=1, padx=5)

        ttk.Label(frm, text="Host:").grid(row=0, column=2, sticky="w")
        self.host_var = tk.StringVar(value="127.0.0.1")
        ttk.Entry(frm, textvariable=self.host_var, width=16).grid(row=0, column=3, padx=5)

        ttk.Label(frm, text="Port:").grid(row=0, column=4, sticky="w")
        self.port_var = tk.StringVar(value="5025")
        ttk.Entry(frm, textvariable=self.port_var, width=8).grid(row=0, column=5, padx=5)

        self.connect_btn = ttk.Button(frm, text="Connect", command=self.on_connect)
        self.connect_btn.grid(row=0, column=6, padx=8)

        ttk.Label(frm, text="IDN:").grid(row=1, column=0, sticky="w", pady=(8,0))
        self.idn_var = tk.StringVar(value="(not connected)")
        ttk.Entry(frm, textvariable=self.idn_var, width=60, state="readonly").grid(row=1, column=1, columnspan=6, sticky="we", pady=(8,0), padx=5)

        # ---- Sweep settings ----
        sweep = ttk.LabelFrame(self, text="Sweep Settings", padding=10)
        sweep.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        ttk.Label(sweep, text="Start (Hz):").grid(row=0, column=0, sticky="w")
        self.start_var = tk.StringVar(value="30000000")
        ttk.Entry(sweep, textvariable=self.start_var, width=16).grid(row=0, column=1, padx=5)

        ttk.Label(sweep, text="Stop (Hz):").grid(row=0, column=2, sticky="w")
        self.stop_var = tk.StringVar(value="1000000000")
        ttk.Entry(sweep, textvariable=self.stop_var, width=16).grid(row=0, column=3, padx=5)

        ttk.Label(sweep, text="Points:").grid(row=0, column=4, sticky="w")
        self.points_var = tk.StringVar(value="1001")
        ttk.Entry(sweep, textvariable=self.points_var, width=10).grid(row=0, column=5, padx=5)

        self.run_btn = ttk.Button(sweep, text="Run", command=self.on_run)
        self.run_btn.grid(row=0, column=6, padx=10)

        self.stop_btn = ttk.Button(sweep, text="Stop", command=self.on_stop, state="disabled")
        self.stop_btn.grid(row=0, column=7, padx=5)

        ttk.Label(sweep, text="Status:").grid(row=1, column=0, sticky="w", pady=(8,0))
        self.status_var = tk.StringVar(value="Idle")
        ttk.Label(sweep, textvariable=self.status_var).grid(row=1, column=1, columnspan=7, sticky="w", pady=(8,0))

        # ---- Plot area ----
        plot_frame = ttk.Frame(self, padding=10)
        plot_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.fig = Figure(figsize=(7, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title("Trace (dBm)")
        self.ax.set_xlabel("Index")
        self.ax.set_ylabel("Amplitude (dBm)")

        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def set_status(self, s: str):
        self.status_var.set(s)
        self.update_idletasks()

    def on_connect(self):
        try:
            backend = self.backend_var.get().strip()
            Instrument = load_instrument(backend)

            host = self.host_var.get().strip()
            port = int(self.port_var.get().strip())

            self.inst = Instrument(host, port)
            self.inst.connect()
            idn = self.inst.idn()
            self.idn_var.set(idn)
            self.connected = True
            self.set_status(f"Connected ({backend})")
        except Exception as e:
            self.connected = False
            self.idn_var.set("(not connected)")
            messagebox.showerror("Connect failed", str(e))
            self.set_status("Connect failed")

    def on_run(self):
        if self.worker and self.worker.is_alive():
            return

        self.stop_requested = False
        self.run_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.set_status("Running...")

        self.worker = threading.Thread(target=self._run_worker, daemon=True)
        self.worker.start()

    def on_stop(self):
        # Simple hackathon stop: prevents new run + updates UI
        self.stop_requested = True
        self.set_status("Stop requested (will stop after current operation)")

    def _run_worker(self):
        try:
            if not self.connected or self.inst is None:
                # auto-connect if not already
                self.after(0, self.on_connect)
                # give UI a moment
                # (no sleeps needed; but keep it simple)
            if self.stop_requested:
                self.after(0, self._finish_run_ui)
                return

            start_hz = float(self.start_var.get().strip())
            stop_hz = float(self.stop_var.get().strip())
            points = int(float(self.points_var.get().strip()))

            # Acquire trace
            self.inst.set_sweep(start_hz, stop_hz, points)
            trace = self.inst.get_trace()

            if self.stop_requested:
                self.after(0, self._finish_run_ui)
                return

            # Save run artifacts (manifest + CSV)
            run_dir = make_run_dir("runs")
            csv_path = os.path.join(run_dir, "trace.csv")
            manifest_path = os.path.join(run_dir, "manifest.json")

            write_trace_csv(csv_path, trace)

            m = RunManifest(
                run_id=os.path.basename(run_dir),
                start_time=now_iso(),
                end_time=now_iso(),
                status="PASS" if len(trace) == points else "FAIL",
                error=None if len(trace) == points else f"Trace length {len(trace)} != {points}",
                host=self.host_var.get().strip(),
                port=int(self.port_var.get().strip()),
                idn=self.idn_var.get(),
                sweep_start_hz=start_hz,
                sweep_stop_hz=stop_hz,
                sweep_points=points,
                trace_csv="trace.csv",
                transcript="(gui_direct)",
            )
            m.write(manifest_path)

            # Plot on UI thread
            self.after(0, lambda: self._plot(trace))
            self.after(0, lambda: self.set_status(f"Saved: {run_dir}"))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Run failed", str(e)))
            self.after(0, lambda: self.set_status(f"Run failed: {e}"))
        finally:
            self.after(0, self._finish_run_ui)

    def _plot(self, trace: list[float]):
        self.ax.clear()
        self.ax.set_title("Trace (dBm)")
        self.ax.set_xlabel("Index")
        self.ax.set_ylabel("Amplitude (dBm)")
        self.ax.plot(list(range(len(trace))), trace)
        self.canvas.draw()

    def _finish_run_ui(self):
        self.run_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
