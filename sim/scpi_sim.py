import socket

HOST = "127.0.0.1"
PORT = 5025

IDN_RESPONSE = "HPE,SIM-SA,0001,0.1\n"

# Step 14: simulator state (defaults)
freq_start = 30e6
freq_stop = 1e9
points = 1001


def handle_client(conn: socket.socket, addr) -> None:
    global freq_start, freq_stop, points

    print(f"[SCPI_SIM] Client connected: {addr}")
    buffer = b""

    with conn:
        while True:
            data = conn.recv(4096)
            if not data:
                print("[SCPI_SIM] Client disconnected")
                return

            # Step 12.c: line-based parsing
            buffer += data
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                cmd = line.decode(errors="ignore").strip()
                if not cmd:
                    continue

                print(f"[SCPI_SIM] RX: {cmd}")
                u = cmd.upper()

                # Step 13: *IDN?
                if u == "*IDN?":
                    response = IDN_RESPONSE

                # ----- Step 15: setters (with common variants) -----

                # FREQ:STAR / FREQ:START
                elif u.startswith("FREQ:STAR ") or u.startswith("FREQ:START "):
                    try:
                        freq_start = float(cmd.split()[-1])
                        response = "OK\n"
                    except ValueError:
                        response = "ERR\n"

                # FREQ:STOP
                elif u.startswith("FREQ:STOP "):
                    try:
                        freq_stop = float(cmd.split()[-1])
                        response = "OK\n"
                    except ValueError:
                        response = "ERR\n"

                # SWE:POIN / SWE:POINTS
                elif u.startswith("SWE:POIN ") or u.startswith("SWE:POINTS "):
                    try:
                        points = int(float(cmd.split()[-1]))
                        response = "OK\n"
                    except ValueError:
                        response = "ERR\n"

                # Optional queries (very useful for testing)
                elif u == "FREQ:STAR?":
                    response = f"{freq_start}\n"
                elif u == "FREQ:STOP?":
                    response = f"{freq_stop}\n"
                elif u in ("SWE:POIN?", "SWE:POINTS?"):
                    response = f"{points}\n"

                elif u == "*OPC?":
                    response = "1\n"

                else:
                    response = "OK\n"

                conn.sendall(response.encode())
                print(f"[SCPI_SIM] TX: {response.strip()}")


def main() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(1)

        print(f"[SCPI_SIM] Listening on {HOST}:{PORT}")

        while True:
            conn, addr = server.accept()
            handle_client(conn, addr)


if __name__ == "__main__":
    main()
