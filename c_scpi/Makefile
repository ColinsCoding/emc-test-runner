CC=gcc
CFLAGS=-Wall -O2 -fPIC
LDFLAGS=-shared
LDLIBS=-lws2_32

all:
	$(CC) $(CFLAGS) $(LDFLAGS) -o libscpi_client.dll scpi_client.c $(LDLIBS)

clean:
	rm -f libscpi_client.dll
