#Just a simple redirect to call bake

export MANTLE=lattice
export MANTLE_TARGET=ice40

TMP := tmp
BINDIR := build

#Fabricate is a terrible and broken build system and should never be used

include Makefrag

SRC_PCFFILES := $(patsubst %.py, $(BINDIR)/%.pcf, $(SRC_PYFILES))
SRC_VFILES := $(patsubst %.py, $(BINDIR)/%.v, $(SRC_PYFILES))

#TODO can't make this parallel yet
$(SRC_PCFFILES) : $(BINDIR)/%.pcf : %.py
	mkdir -p $(TMP)
	python2 $< build/$* \
        |& tee $(TMP)/magma.out
	@if grep -i "Warn\|Error" $(TMP)/magma.out > /dev/null; \
	then echo "Stopping due to warning and/or error:"; \
	grep -i "Warn\|Error" $(TMP)/magma.out | head -n 1; \
        echo "Aborting"; \
	exit 1; \
	fi

build/ftdi.bin : $(SRC_PCFFILES)
	pushd build && make

all: build/ftdi.bin

upload: all
	pushd build && make upload

clean:
	rm -f *.pyc
	rm -rf __pycache__
	pushd build && rm -f *.pcf *.v *.pyc
	pushd build && make clean

.DEFAULT_GOAL := all
.PHONY: all clean upload
.DELETE_ON_ERROR:
