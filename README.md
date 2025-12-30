# EMC Test Runner (SCPI + Simulator + GUI)

A small EMC test automation framework inspired by real EMC lab workflows.
It demonstrates SCPI-over-TCP instrument control, automated sweeps, trace capture,
and traceable run artifacts (CSV + JSON manifest + transcript).

## Features
- **SCPI client over TCP** (Python backend)
- Optional **C backend** (ctypes wrapper) for low-level transport experiments
- **SCPI instrument simulator** for development/testing without hardware
- **Run artifacts** per sweep:
  - `trace.csv` (captured amplitude trace)
  - `manifest.json` (run metadata: host, IDN, sweep params, status, errors)
  - `transcript.txt` (command/error transcript)
- **GUI** (Tkinter + Matplotlib) to connect, run sweeps, and visualize traces
- Basic tests against the simulator (`pytest`)

## Project layout
- `core/` instrument abstractions, logging, run manifest utilities
- `sim/` SCPI simulator server
- `gui/` Tkinter GUI application
- `c_scpi/` C client + build scripts (optional backend)
- `tests/` automated + manual test helpers
- `run_scpi_sweep.py` CLI sweep runner / CSV writer

## Quickstart

### 1) Create a virtualenv + install deps
```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# build C backend
.\build.ps1

# Terminal A: start simulator
python .\sim\scpi_sim.py --seed 1234 --error-rate 0.02 --drop-rate 0.01

# Terminal B: run tests (Python backend)
$env:SCPI_BACKEND="py"; python .\tests\test_scpi_basic.py

# Terminal B: run tests (C backend)
$env:SCPI_BACKEND="c"; python .\tests\test_scpi_basic.py

# Run a sweep and save artifacts
python .\run_scpi_sweep.py

# Run GUI
python -m gui.app
```

## Notes
- The SCPI simulator is basic and intended for demonstration only.
- The C backend is optional and provided for experimentation with low-level transport.
- The GUI is minimal and can be extended with more features as needed.
- The project is structured for clarity and ease of understanding SCPI workflows in EMC testing.
- Contributions and improvements are welcome!


<!-- refresh contributors -->

