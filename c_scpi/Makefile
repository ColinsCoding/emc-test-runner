CC=gcc
CFLAGS=-Wall -O2 -fPIC
TARGET=libscpi_client

ifeq ($(OS),Windows_NT)
    EXT=.dll
else
    EXT=.so
endif

all:
	$(CC) $(CFLAGS) -shared -o $(TARGET)$(EXT) scpi_client.c

clean:
	rm -f $(TARGET).so $(TARGET).dll
