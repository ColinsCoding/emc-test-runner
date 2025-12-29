import socket

HOST = "127.0.0.1"
PORT = 5025

IDN_RESPONSE = "HPE,SIM-SA,0001,0.1\n"

def handle_client(conn: socket.socket, addr) -> None:
    print(f"[SCPI_SIM] Client connected: {addr}")
    buffer = b""

    with conn:
        while True:
            data = conn.recv(4096)
            if not data:
                print("[SCPI_SIM] Client disconnected")
                return

            buffer += data
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                cmd = line.decode(errors="ignore").strip()
                if not cmd:
                    continue

                print(f"[SCPI_SIM] RX: {cmd}")

                u = cmd.upper()
                if u == "*IDN?":
                    response = IDN_RESPONSE
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
