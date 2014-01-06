CC = gcc
IDIR = /usr/local/include
LDIR = /usr/local/lib
LIBS = -lzmq
CFLAGS = -I${IDIR} -L${LDIR}

all: vpoller_cclient_clean vpoller_cclient

clean: vpoller_cclient_clean

vpoller_cclient:
	$(CC) $(CFLAGS) vpoller-cclient.c -o vpoller-cclient $(LIBS)

vpoller_cclient_clean:
	@rm -rf vpoller-cclient
	@echo "Cleaning target vpoller-cclient"

