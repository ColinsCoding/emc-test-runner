"""
scpi_sim.py — Minimal SCPI (Standard Commands for Programmable Instruments) simulator over TCP/IP.

This module implements a very small TCP server that simulates a SCPI-capable
instrument. SCPI is a standardized, ASCII-based command language used to control
test and measurement equipment (such as oscilloscopes, signal generators, and
power supplies) over interfaces like GPIB, USB, and TCP/IP.

Transport and protocol details:
- Transport: TCP/IP using IPv4 sockets
- Default address: 127.0.0.1 (loopback only)
- Default port: 5025 (commonly used for SCPI over TCP)
- Message framing: newline ('\\n') terminated ASCII commands
- Encoding: ASCII-compatible text

Server behavior:
- Accepts exactly one client connection
- Processes incoming data line-by-line
- Runs synchronously until the client disconnects
- No concurrency, authentication, or timeout handling
- Intended for local testing and simulation only

Supported SCPI commands:
- *IDN?  -> returns a fixed instrument identification string
- *OPC?  -> returns "1" to indicate immediate operation completion
- Any other command is acknowledged with "OK"

This implementation is intentionally minimal and is NOT a full SCPI parser
or standards-compliant instrument. It is suitable for:
- Testing SCPI client software
- Test automation development
- Simulating basic instrument communication during EMC or lab testing
"""

import socket

HOST = "127.0.0.1"
PORT = 5025


def main() -> None:
    """
    Start a minimal single-client SCPI-over-TCP server.

    The server listens on HOST:PORT, accepts one client connection,
    and responds to newline-terminated SCPI commands until the client
    disconnects.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(1)

        print(f"[SCPI_SIM] Listening on {HOST}:{PORT} (1 client max)")
        conn, addr = server.accept()
        print(f"[SCPI_SIM] Client connected: {addr}")

        with conn:
            buf = b""
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    print("[SCPI_SIM] Client disconnected")
                    break

                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    cmd = line.decode(errors="ignore").strip()
                    if not cmd:
                        continue

                    print(f"[SCPI_SIM] RX: {cmd}")
                    u = cmd.upper()

                    if u == "*IDN?":
                        reply = "HPE,SCPI_SIM,EMC_TEST_RUNNER,0.1\n"
                    elif u == "*OPC?":
                        reply = "1\n"
                    else:
                        reply = "OK\n"

                    conn.sendall(reply.encode())
                    print(f"[SCPI_SIM] TX: {reply.strip()}")


if __name__ == "__main__":
    main()
