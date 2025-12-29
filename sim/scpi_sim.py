import socket
import math
import random

HOST = "127.0.0.1"
PORT = 5025

IDN_RESPONSE = "HPE,SIM-SA,0001,0.1\n"

# State (defaults)
freq_start = 30e6
freq_stop = 1e9
points = 1001
armed = False


def make_trace_dbm(f_start: float, f_stop: float, npts: int) -> list[float]:
    """
    Step 18: "realistic-ish" trace in dBm:
      - noise floor with randomness
      - two Gaussian peaks
    Returns a list of amplitudes (length npts).
    """
    if npts <= 1:
        return [-90.0]

    span = max(f_stop - f_start, 1.0)
    df = span / (npts - 1)

    # Noise floor around -90 dBm with ~2 dB randomness
    noise_mu = -90.0
    noise_sigma = 2.0

    # Two peaks somewhere in-span
    p1_center = f_start + 0.20 * span
    p2_center = f_start + 0.65 * span
    p1_width = 0.03 * span
    p2_width = 0.06 * span

    # Peak heights above noise floor
    p1_height = 25.0   # dB above floor
    p2_height = 18.0

    out = []
    for i in range(npts):
        f = f_start + i * df

        # base noise
        a = random.gauss(noise_mu, noise_sigma)

        # gaussian bumps (additive in dB-ish for a simple fake)
        g1 = p1_height * math.exp(-0.5 * ((f - p1_center) / p1_width) ** 2)
        g2 = p2_height * math.exp(-0.5 * ((f - p2_center) / p2_width) ** 2)

        out.append(a + g1 + g2)

    return out


def handle_client(conn: socket.socket, addr) -> None:
    global freq_start, freq_stop, points, armed

    print(f"[SCPI_SIM] Client connected: {addr}")
    buffer = b""

    with conn:
        while True:
            data = conn.recv(4096)
            if not data:
                print("[SCPI_SIM] Client disconnected")
                return

            # Step 12.c: line-based command parsing
            buffer += data
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                cmd = line.decode(errors="ignore").strip()
                if not cmd:
                    continue

                # Step 19: log each received command
                print(f"[SCPI_SIM] RX: {cmd}")

                u = cmd.upper()

                # *IDN?
                if u == "*IDN?":
                    response = IDN_RESPONSE

                # INIT / INIT:IMM (arm measurement)
                elif u in ("INIT", "INIT:IMM"):
                    armed = True
                    response = "OK\n"

                # Optional: query arm state
                elif u == "INIT?":
                    response = ("1\n" if armed else "0\n")

                # Step 15 setters (accept common variants)
                elif u.startswith("FREQ:STAR ") or u.startswith("FREQ:START "):
                    try:
                        freq_start = float(cmd.split()[-1])
                        response = "OK\n"
                    except ValueError:
                        response = "ERR\n"

                elif u.startswith("FREQ:STOP "):
                    try:
                        freq_stop = float(cmd.split()[-1])
                        response = "OK\n"
                    except ValueError:
                        response = "ERR\n"

                elif u.startswith("SWE:POIN ") or u.startswith("SWE:POINTS "):
                    try:
                        points = int(float(cmd.split()[-1]))
                        response = "OK\n"
                    except ValueError:
                        response = "ERR\n"

                # Optional queries (helpful for debug/tests)
                elif u == "FREQ:STAR?":
                    response = f"{freq_start}\n"
                elif u == "FREQ:STOP?":
                    response = f"{freq_stop}\n"
                elif u in ("SWE:POIN?", "SWE:POINTS?"):
                    response = f"{points}\n"

                # Step 17: TRAC? returns comma-separated amplitudes
                elif u in ("TRAC?", "TRAC:DATA?"):
                    # In real instruments, you'd often need INIT first.
                    # We'll allow it either way, but if not armed, still return data.
                    amps = make_trace_dbm(freq_start, freq_stop, points)
                    # Comma-separated list of floats
                    response = ",".join(f"{a:.2f}" for a in amps) + "\n"
                    # Optionally auto-clear armed to mimic one-shot capture
                    armed = False

                # Operation complete
                elif u == "*OPC?":
                    response = "1\n"

                else:
                    response = "OK\n"

                conn.sendall(response.encode())
                print(f"[SCPI_SIM] TX: {response[:80].strip()}{'...' if len(response) > 80 else ''}")


def main() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(1)

        # Step 20: confirm it listens on 5025
        print(f"[SCPI_SIM] Listening on {HOST}:{PORT}")

        while True:
            conn, addr = server.accept()
            handle_client(conn, addr)


if __name__ == "__main__":
    main()
