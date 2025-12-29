#include "scpi_client.h"

#include <stdio.h>
#include <string.h>

#ifdef _WIN32
  #include <winsock2.h>
  #include <ws2tcpip.h>
  #pragma comment(lib, "Ws2_32.lib")
  typedef SOCKET scpi_sock_t;
  #define SCPI_INVALID_SOCK INVALID_SOCKET
  #define scpi_close_sock closesocket
#else
  #include <unistd.h>
  #include <errno.h>
  #include <sys/types.h>
  #include <sys/socket.h>
  #include <netdb.h>
  typedef int scpi_sock_t;
  #define SCPI_INVALID_SOCK (-1)
  #define scpi_close_sock close
#endif


static int ensure_winsock(void) {
#ifdef _WIN32
    static int initialized = 0;
    if (!initialized) {
        WSADATA wsa;
        if (WSAStartup(MAKEWORD(2,2), &wsa) != 0) return -1;
        initialized = 1;
    }
#endif
    return 0;
}

int scpi_connect(const char* host, int port) {
    if (!host) return -1;
    if (ensure_winsock() != 0) return -1;

    char port_str[16];
    snprintf(port_str, sizeof(port_str), "%d", port);

    struct addrinfo hints;
    memset(&hints, 0, sizeof(hints));
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_family = AF_UNSPEC;

    struct addrinfo* res = NULL;
    int rc = getaddrinfo(host, port_str, &hints, &res);
    if (rc != 0 || !res) return -1;

    scpi_sock_t s = SCPI_INVALID_SOCK;

    for (struct addrinfo* p = res; p != NULL; p = p->ai_next) {
        s = (scpi_sock_t)socket(p->ai_family, p->ai_socktype, p->ai_protocol);
        if (s == SCPI_INVALID_SOCK) continue;

        if (connect(s, p->ai_addr, (int)p->ai_addrlen) == 0) {
            freeaddrinfo(res);
#ifdef _WIN32
            return (int)s;  // SOCKET fits in int for typical use here
#else
            return s;
#endif
        }

        scpi_close_sock(s);
        s = SCPI_INVALID_SOCK;
    }

    freeaddrinfo(res);
    return -1;
}

int scpi_write(int sock, const char* cmd) {
    if (!cmd) return -1;

    // Ensure newline at end
    char buf[2048];
    size_t n = strlen(cmd);
    if (n + 2 > sizeof(buf)) return -1;

    memcpy(buf, cmd, n);
    if (n == 0 || cmd[n - 1] != '\n') {
        buf[n++] = '\n';
    }
    buf[n] = '\0';

#ifdef _WIN32
    int sent = send((SOCKET)sock, buf, (int)n, 0);
#else
    int sent = (int)send(sock, buf, n, 0);
#endif
    return (sent == (int)n) ? 0 : -1;
}

int scpi_query(int sock, const char* cmd, char* out, int out_sz) {
    if (!cmd || !out || out_sz <= 1) return -1;

    out[0] = '\0';

    if (scpi_write(sock, cmd) != 0) return -1;

    int used = 0;
    while (used < out_sz - 1) {
        char c = 0;
#ifdef _WIN32
        int r = recv((SOCKET)sock, &c, 1, 0);
#else
        int r = (int)recv(sock, &c, 1, 0);
#endif
        if (r <= 0) break;

        out[used++] = c;
        if (c == '\n') break;
    }

    out[used] = '\0';
    return used > 0 ? 0 : -1;
}

void scpi_close(int sock) {
#ifdef _WIN32
    closesocket((SOCKET)sock);
#else
    close(sock);
#endif
}
