import socket
import math
import random
import argparse
import time


HOST = "127.0.0.1"
PORT = 5025

IDN_RESPONSE = "HPE,SIM-SA,0001,0.1\n"

# State (defaults)
freq_start = 30e6
freq_stop = 1e9
points = 1001
armed = False

rng = random.Random()   # use our own RNG for determinism
error_rate = 0.0
drop_rate = 0.0


def make_trace(points: int) -> str:
    # Noise floor around -90 dBm, plus two Gaussian peaks
    noise_mu = -90.0
    noise_sigma = 2.0

    # peaks positioned in normalized index-space (0..1)
    p1_center = 0.20
    p2_center = 0.65
    p1_width = 0.03
    p2_width = 0.06
    p1_height = 25.0
    p2_height = 18.0

    vals = []
    for i in range(points):
        x = i / max(points - 1, 1)
        a = rng.gauss(noise_mu, noise_sigma)
        g1 = p1_height * math.exp(-0.5 * ((x - p1_center) / p1_width) ** 2)
        g2 = p2_height * math.exp(-0.5 * ((x - p2_center) / p2_width) ** 2)
        vals.append(a + g1 + g2)

    return ",".join(f"{v:.2f}" for v in vals) + "\n"


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

def maybe_inject_drop(conn: socket.socket) -> bool:
    """Return True if we intentionally dropped the connection."""
    if drop_rate > 0.0 and rng.random() < drop_rate:
        try:
            conn.close()
        finally:
            return True
    return False


def maybe_inject_error(u_cmd: str) -> str | None:
    """
    Return an error response string (ending in \\n) or None.
    We only inject timeouts for queries (commands ending with '?').
    """
    if not u_cmd.endswith("?"):
        return None
    if error_rate > 0.0 and rng.random() < error_rate:
        return "ERROR:SIM_TIMEOUT\n"
    return None



def handle_client(conn: socket.socket, addr) -> None:
    global freq_start, freq_stop, points, armed

    print(f"[SCPI_SIM] Client connected: {addr}")
    buffer = b""

    with conn:
        while True:
            try:
                data = conn.recv(4096)
            except (ConnectionResetError, ConnectionAbortedError, OSError) as e:
                print(f"[SCPI_SIM] Client disconnected (reset): {e}")
                return

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

                if maybe_inject_drop(conn):
                    print("[SCPI_SIM] Injected connection drop")
                    return
                
                err = maybe_inject_error(u)
                if err is not None:
                    response = err
                    # Send response (query expects a line), then continue
                    try:
                        conn.sendall(response.encode())
                    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError) as e:
                        print(f"[SCPI_SIM] Send failed (client dropped): {e}")
                        return
                    print(f"[SCPI_SIM] TX: {response.strip()}")
                    continue

                # *IDN?
                if u == "*IDN?":
                    response = IDN_RESPONSE

                # INIT / INIT:IMM (arm measurement)
                elif u in ("INIT", "INIT:IMM"):
                    armed = True
                    response = ""

                # Optional: query arm state
                elif u == "INIT?":
                    response = ("1\n" if armed else "0\n")

                # Step 15 setters (accept common variants)
                elif u.startswith("FREQ:STAR ") or u.startswith("FREQ:START "):
                    try:
                        freq_start = float(cmd.split()[-1])
                        response = ""
                    except ValueError:
                        response = "ERR\n"

                elif u.startswith("FREQ:STOP "):
                    try:
                        freq_stop = float(cmd.split()[-1])
                        response = ""
                    except ValueError:
                        response = "ERR\n"

                elif u.startswith("SWE:POIN ") or u.startswith("SWE:POINTS "):
                    try:
                        points = int(float(cmd.split()[-1]))
                        response = ""
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

                if response:
                    try:
                        conn.sendall(response.encode())
                    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError) as e:
                        print(f"[SCPI_SIM] Send failed (client dropped): {e}")
                        return

                print(f"[SCPI_SIM] TX: {response[:80].strip()}{'...' if len(response) > 80 else ''}")


def main() -> None:
    global rng, error_rate, drop_rate


    ap = argparse.ArgumentParser(
        description="SCPI simulator with determinism and fault injection"
    )
    ap.add_argument("--seed", type=int, default=None,
                    help="Seed RNG for deterministic traces")
    ap.add_argument("--error-rate", type=float, default=0.0,
                    help="Probability of ERROR:SIM_TIMEOUT on queries")
    ap.add_argument("--drop-rate", type=float, default=0.0,
                    help="Probability of dropping the socket")
    args = ap.parse_args()

    # ---- RNG setup ----
    if args.seed is not None:
        rng = random.Random(args.seed)
        print(f"[SCPI_SIM] Deterministic mode enabled (seed={args.seed})")
    else:
        rng = random.Random()

    # Clamp rates to [0,1]
    error_rate = max(0.0, min(1.0, args.error_rate))
    drop_rate = max(0.0, min(1.0, args.drop_rate))

    print(f"[SCPI_SIM] error_rate={error_rate:.3f}, drop_rate={drop_rate:.3f}")

    # ---- TCP server setup ----
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(1)

        # Important for Ctrl-C on Windows
        server.settimeout(1.0)

        print(f"[SCPI_SIM] Listening on {HOST}:{PORT}")

        try:
            while True:
                try:
                    conn, addr = server.accept()
                except socket.timeout:
                    continue  # allow Ctrl-C to be processed

                handle_client(conn, addr)

        except KeyboardInterrupt:
            print("\n[SCPI_SIM] Shutdown requested (Ctrl-C)")

        finally:
            print("[SCPI_SIM] Simulator stopped")



if __name__ == "__main__":
    main()
