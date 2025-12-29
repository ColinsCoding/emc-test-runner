#pragma once

#ifdef __cplusplus
extern "C" {
#endif

int scpi_connect(const char* host, int port);
int scpi_write(int sock, const char* cmd);
int scpi_query(int sock, const char* cmd, char* out, int out_sz);
void scpi_close(int sock);

#ifdef __cplusplus
}
#endif
