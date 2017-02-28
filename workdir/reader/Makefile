LDLIBS = -lftdi1 -lm
CFLAGS = -MD -O0 -ggdb -Wall -std=c99 -I/usr/include/libftdi1

CFLAGS += -Wno-unused-label -Wno-unused-variable -Wno-unused-function

#LDLIBS += $(shell for pkg in libftdi1 libftdi; do $(PKG_CONFIG) --silence-errors --libs $$pkg && exit; done; echo -lftdi; )
#CFLAGS += $(shell for pkg in libftdi1 libftdi; do $(PKG_CONFIG) --silence-errors --cflags $$pkg && exit; done; )

all: reader

reader: reader.o
	$(CC) -o $@ $(LDFLAGS) $^ $(LDLIBS)

clean:
	rm -f reader
	rm -f *.o *.d

-include *.d

.PHONY: all install uninstall clean
