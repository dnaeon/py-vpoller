CC = gcc
IDIR = /usr/local/include
LDIR = /usr/local/lib
LIBS = -lzmq
CFLAGS = -I${IDIR} -L${LDIR}

all: vmpoller_cclient_clean vmpoller_cclient

clean: vmpoller_cclient_clean

vmpoller_cclient:
	$(CC) $(CFLAGS) vmpoller-cclient.c -o vmpoller-cclient $(LIBS)

vmpoller_cclient_clean:
	@rm -rf vmpoller-cclient
	@echo "Cleaning target vmpoller-cclient"

