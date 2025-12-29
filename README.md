# EMC Test Runner

## What this is
This project is a small EMC test automation framework inspired by real-world
electromagnetic compatibility (EMC) laboratories. It is designed to demonstrate
instrument control, test sequencing, data acquisition, and traceable results
logging similar to workflows used in ISO/IEC 17025–accredited test labs.
The system uses Python for orchestration and user-facing logic, with optional
C components for low-level or performance-critical functionality.

## Day 1 goal: SCPI over TCP
The initial goal is to implement SCPI communication over TCP/IP between a
simulated EMC instrument (e.g., spectrum analyzer or EMI receiver) and a Python
client. This includes sending basic SCPI commands (such as `*IDN?`, frequency
setup, and trace acquisition) and verifying end-to-end connectivity using a
simple test script. This establishes the foundation for later automation,
logging, and GUI development.
