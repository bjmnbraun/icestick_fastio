# Icestick Fast IO

* Team Members: Benjamin Braun, Nate Chizgi

### Goal of the project

* Make more specific, offering streaming interface to FPGA

To turn the icestick into a platform for writing visual programs. The icestick
is a cheap and easy-to-obtain piece of hardware, and our goal is to lower the
barrier of entry to programming small, but satisfying, programs on the device.
Our hope is to allow those without a programming background to experiment
creatively with the capabilities of a small FPGA.

### Deliverables

A fast, bidirectional, streaming interface to the icestick FPGA.

A simple platform for programming visual programs on the icestick, and multiple
interesting visuals generated on the icestick but shown real-time on the computer screen.

### Challenges

The icestorm pipeline comes equipped to flash a static program to the device,
but offers few capabilities for streaming I/O while a program is running. Since
we need to stream large images off of (and possibly back on to) to the FPGA many times
a second, we need to overcome the limited I/O capabilities of the icestick.

Other FPGAs may come with special I/O capabilities. Our goal is to specifically
implement a high-throughput I/O solution for the off-the-shelf icestick.

### Previous work in this area

* UART RX example given in class.

* Ross demonstrated real time edge detection in class.

* Streaming I/O available through SRAM on icestick with some modification to the device.

The [processing project](www.processing.org) has been successful at attracting
artists and creators with little programming experience to programming. In
fact, we plan to model some of our demo programs off of processing's demos
(such as rendering fire via an old-skool pixel effect.)

The [openframeworks project](openframeworks.cc) is a translation of processing to the C/C++ language by the same development team. We plan to use openframeworks as an easy way to display images generated from the FPGA on the computer screen.

## Plan and timeline

### I/O throughput goal

* Back of the envelope possible and ideal throughput

### Optimizing Pat's UART

* Pat provides a UART that we plan to use as the starting point for our I/O
stream.

We plan to extend this UART to

* Use parallel pins. The icestick has XXX pins and these can be used to run a
UART in parallel. Understanding how to do this requires studing the FTDI
interface and the UART code. Ben and Nate will both look into whether this is
possible.

* Overclock the FPGA. The throughput of the UART can be increased by increasing
the clock-rate of the FPGA. Ben will look into this.

We plan to have one of the above items working for the March 7 presentation.
A version with higher throughput will be presented March 21.

### Implementing bi-directional UART

* Pat's UART is only for reading data off the FPGA, we plan to extend it with
capabilities to send in either direction. Nate will look into this.

We plan to have this working for the March 7 presentation.

### Predicting and measuring throughput of the I/O stream

* Ben will conduct metrics and make graphs on the throughput of the I/O system
for both presentations.

### Visual program based on interface

* Ben will write a simple template visual program that streams a generated
image off of the FPGA and displays on the computer.

* Ben and Nate will write simple visual programs based on this template. These
will be presented on March 21.
