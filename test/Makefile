export MANTLE=lattice
export MANTLE_TARGET=ice40

TMP := tmp
BINDIR := bin

#Defines APPS_PYFILES
include src/Makefrag

APPS_PCFFILES := $(patsubst %.py, $(BINDIR)/%/app.pcf, $(APPS_PYFILES))
APPS_BINFILES := $(patsubst %.py, $(BINDIR)/%/app.bin, $(APPS_PYFILES))
APPS_IOBINARIES := $(patsubst %.py, $(BINDIR)/%/app, $(APPS_PYFILES))

#TODO autoparallelize

LDLIBS = -lftdi1 -lm -lusb-1.0
CFLAGS = -MD -O0 -ggdb -Wall -std=gnu99 -I/usr/include/libftdi1 -I/usr/include/libusb-1.0
CFLAGS += -Wno-unused-label -Wno-unused-variable -Wno-unused-function

$(APPS_PCFFILES) : ../fastio/py/**

$(APPS_PCFFILES) : $(BINDIR)/%/app.pcf : %.py
	mkdir -p $(TMP)/$*
	mkdir -p $(@D)
	python2 $< $(BINDIR)/$*/app \
        |& tee $(TMP)/$*/out.txt
	@if grep -i "Warn\|Error" $(TMP)/$*/out.txt > /dev/null; \
	then echo "Stopping due to warning and/or error:"; \
	grep -i "Warn\|Error" $(TMP)/$*/out.txt | head -n 1; \
        echo "Aborting"; \
	exit 1; \
	fi

DEVICE := 1k
QUIET := -q
$(APPS_BINFILES) : $(BINDIR)/%/app.bin : $(BINDIR)/%/app.pcf
	pushd $(@D) && \
yosys $(QUIET) -p 'synth_ice40 -top main -blif app.blif' app.v && \
arachne-pnr $(QUIET) -d $(DEVICE) -o app.txt -p app.pcf app.blif && \
icepack app.txt app.bin

$(APPS_IOBINARIES) : ../fastio/iocc/**

$(APPS_IOBINARIES) : $(BINDIR)/%/app : $(BINDIR)/%/app.pcf
	iocc $(BINDIR)/$*/app.iospec.json $(BINDIR)/$*/app
	$(CC) -o $@ $(LDFLAGS) $(LDLIBS) $(BINDIR)/$*/app-io.c $(CFLAGS)

all: $(APPS_BINFILES) $(APPS_IOBINARIES)

#app-upload is a pseudofile never created, so upload always reuploads
APPS_UPLOADS := $(patsubst %.py, $(BINDIR)/%/app-upload, $(APPS_PYFILES))
$(APPS_UPLOADS) : $(BINDIR)/%/app-upload : $(BINDIR)/%/app.bin $(BINDIR)/%/app
	pushd $(@D) && \
iceprog app.bin

upload: $(APPS_UPLOADS)

clean:
	rm -rf $(BINDIR)
	rm -rf $(TMP)
	rm -f *.pyc
	rm -rf __pycache__

.DEFAULT_GOAL := all
.PHONY: all clean upload
.DELETE_ON_ERROR:
