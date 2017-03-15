export MANTLE=lattice
export MANTLE_TARGET=ice40

TMP := tmp
BINDIR := bin

#Defines APPS_PYFILES
include src/Makefrag

APPS_PCFFILES := $(patsubst %.py, $(BINDIR)/%/app.pcf, $(APPS_PYFILES))
APPS_BINFILES := $(patsubst %.py, $(BINDIR)/%/app.bin, $(APPS_PYFILES))

#TODO autoparallelize

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

all: $(APPS_BINFILES)

#app-upload is a pseudofile never created, so upload always reuploads
APPS_UPLOADS := $(patsubst %.py, $(BINDIR)/%/app-upload, $(APPS_PYFILES))
$(APPS_UPLOADS) : $(BINDIR)/%/app-upload : $(BINDIR)/%/app.bin
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
