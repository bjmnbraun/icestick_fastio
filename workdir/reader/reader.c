/*
 *  reader - readers from serial port on icestick
 *
 *  Copyright (C) 2015  Clifford Wolf <clifford@clifford.at>
 *  
 *  Permission to use, copy, modify, and/or distribute this software for any
 *  purpose with or without fee is hereby granted, provided that the above
 *  copyright notice and this permission notice appear in all copies.
 *  
 *  THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
 *  WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
 *  MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
 *  ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
 *  WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
 *  ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
 *  OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 *
 *  Relevant Documents:
 *  -------------------
 *  http://www.latticesemi.com/~/media/Documents/UserManuals/EI/icestickusermanual.pdf
 *  http://www.micron.com/~/media/documents/products/data-sheet/nor-flash/serial-nor/n25q/n25q_32mb_3v_65nm.pdf
 *  http://www.ftdichip.com/Support/Documents/AppNotes/AN_108_Command_Processor_for_MPSSE_and_MCU_Host_Bus_Emulation_Modes.pdf
 */

#define _GNU_SOURCE

#include <ftdi.h>
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include <signal.h>
#include <sys/types.h>
#include <sys/stat.h>

struct ftdi_context ftdic;
bool ftdic_open = false;
bool verbose = false;

void check_rx()
{
	while (1) {
		uint8_t data;
		int rc = ftdi_read_data(&ftdic, &data, 1);
		if (rc <= 0) break;
		fprintf(stderr, "unexpected rx byte: %02X\n", data);
	}
}

void error()
{
	//check_rx();
	fprintf(stderr, "ABORT.\n");
	if (ftdic_open)
		ftdi_usb_close(&ftdic);
	ftdi_deinit(&ftdic);
	exit(1);
}

uint8_t recv_byte()
{
	uint8_t data;
	while (1) {
		int rc = ftdi_read_data(&ftdic, &data, 1);
		if (rc < 0) {
			fprintf(stderr, "Read error.\n");
			error();
		}
		if (rc == 1)
			break;
		usleep(100);
	}
	return data;
}

void send_byte(uint8_t data)
{
	int rc = ftdi_write_data(&ftdic, &data, 1);
	if (rc != 1) {
		fprintf(stderr, "Write error (single byte, rc=%d, expected %d).\n", rc, 1);
		error();
	}
}

void send_spi(uint8_t *data, int n)
{
	if (n < 1)
		return;

	send_byte(0x11);
	send_byte(n-1);
	send_byte((n-1) >> 8);

	int rc = ftdi_write_data(&ftdic, data, n);
	if (rc != n) {
		fprintf(stderr, "Write error (chunk, rc=%d, expected %d).\n", rc, n);
		error();
	}
}

void xfer_spi(uint8_t *data, int n)
{
	if (n < 1)
		return;

	send_byte(0x31);
	send_byte(n-1);
	send_byte((n-1) >> 8);

	int rc = ftdi_write_data(&ftdic, data, n);
	if (rc != n) {
		fprintf(stderr, "Write error (chunk, rc=%d, expected %d).\n", rc, n);
		error();
	}

	for (int i = 0; i < n; i++)
		data[i] = recv_byte();
}

void set_gpio(int slavesel_b, int creset_b)
{
	uint8_t gpio = 1;

	if (slavesel_b) {
		// ADBUS4 (GPIOL0)
		gpio |= 0x10;
	}

	if (creset_b) {
		// ADBUS7 (GPIOL3)
		gpio |= 0x80;
	}

	send_byte(0x80);
	send_byte(gpio);
	send_byte(0x93);
}

int get_cdone()
{
	uint8_t data;
	send_byte(0x81);
	data = recv_byte();
	// ADBUS6 (GPIOL2)
	return (data & 0x40) != 0;
}

void flash_read_id()
{
	// fprintf(stderr, "read flash ID..\n");

	uint8_t data[21] = { 0x9F };
	set_gpio(0, 0);
	xfer_spi(data, 21);
	set_gpio(1, 0);

	fprintf(stderr, "flash ID:");
	for (int i = 1; i < 21; i++)
		fprintf(stderr, " 0x%02X", data[i]);
	fprintf(stderr, "\n");
}

void flash_power_up()
{
	uint8_t data[1] = { 0xAB };
	set_gpio(0, 0);
	xfer_spi(data, 1);
	set_gpio(1, 0);
}

void flash_power_down()
{
	uint8_t data[1] = { 0xB9 };
	set_gpio(0, 0);
	xfer_spi(data, 1);
	set_gpio(1, 0);
}

void flash_write_enable()
{
	if (verbose)
		fprintf(stderr, "write enable..\n");

	uint8_t data[1] = { 0x06 };
	set_gpio(0, 0);
	xfer_spi(data, 1);
	set_gpio(1, 0);
}

void flash_bulk_erase()
{
	fprintf(stderr, "bulk erase..\n");

	uint8_t data[1] = { 0xc7 };
	set_gpio(0, 0);
	xfer_spi(data, 1);
	set_gpio(1, 0);
}

void flash_64kB_sector_erase(int addr)
{
	fprintf(stderr, "erase 64kB sector at 0x%06X..\n", addr);

	uint8_t command[4] = { 0xd8, (uint8_t)(addr >> 16), (uint8_t)(addr >> 8), (uint8_t)addr };
	set_gpio(0, 0);
	send_spi(command, 4);
	set_gpio(1, 0);
}

void flash_prog(int addr, uint8_t *data, int n)
{
	if (verbose)
		fprintf(stderr, "prog 0x%06X +0x%03X..\n", addr, n);

	uint8_t command[4] = { 0x02, (uint8_t)(addr >> 16), (uint8_t)(addr >> 8), (uint8_t)addr };
	set_gpio(0, 0);
	send_spi(command, 4);
	send_spi(data, n);
	set_gpio(1, 0);

	if (verbose)
		for (int i = 0; i < n; i++)
			fprintf(stderr, "%02x%c", data[i], i == n-1 || i % 32 == 31 ? '\n' : ' ');
}

void flash_read(int addr, uint8_t *data, int n)
{
	if (verbose)
		fprintf(stderr, "read 0x%06X +0x%03X..\n", addr, n);

	uint8_t command[4] = { 0x03, (uint8_t)(addr >> 16), (uint8_t)(addr >> 8), (uint8_t)addr };
	set_gpio(0, 0);
	send_spi(command, 4);
	memset(data, 0, n);
	xfer_spi(data, n);
	set_gpio(1, 0);

	if (verbose)
		for (int i = 0; i < n; i++)
			fprintf(stderr, "%02x%c", data[i], i == n-1 || i % 32 == 31 ? '\n' : ' ');
}

void flash_wait()
{
	if (verbose)
		fprintf(stderr, "waiting..");

	while (1)
	{
		uint8_t data[2] = { 0x05 };

		set_gpio(0, 0);
		xfer_spi(data, 2);
		set_gpio(1, 0);

		if ((data[1] & 0x01) == 0)
			break;

		if (verbose) {
			fprintf(stderr, ".");
			fflush(stdout);
		}
		usleep(1000);
	}

	if (verbose)
		fprintf(stderr, "\n");
}

bool exitRequested = false;

static void
sigintHandler(int signum)
{
        exitRequested = 1;
}

bool CONFIG_DUMP_READ = true;

static int readCallback(
        uint8_t *buffer,
        int length,
        FTDIProgressInfo *progress,
        void *userdata
) {

        if (CONFIG_DUMP_READ){
                printf("Read %d", length);
        }

        if (exitRequested){
                goto out;
        }

        if(length >= 0 && CONFIG_DUMP_READ){
                size_t i = 0;
                for(i = 0; i < length; i++){
                        char c = buffer[i];
                        if (c > 0x02){
                                printf("%c",c);
                        }
                }
        }
        //XXX
        CONFIG_DUMP_READ = false;
        if (progress){
                printf("\n");
                printf("Rate %7.3f", progress->currentRate / (1024.0*1024.0));
        }

out:
        return exitRequested ? 1 : 0;
}

int main(int argc, char **argv)
{
	int read_size = 256 * 1024;
	int rw_offset = 0;

	bool read_mode = false;
	bool check_mode = false;
	bool bulk_erase = false;
	bool dont_erase = false;
	bool prog_sram = false;
	bool test_mode = false;
	const char *filename = NULL;
	const char *devstr = NULL;

        //Interface A might be the flash channel and B the UART?
	//enum ftdi_interface ifnum = INTERFACE_A;
	enum ftdi_interface ifnum = INTERFACE_B;

	int opt;
	char *endptr;

        signal(SIGINT, sigintHandler);

	// ---------------------------------------------------------
	// Initialize USB connection to FT2232H
	// ---------------------------------------------------------

	fprintf(stderr, "init..\n");

	ftdi_init(&ftdic);
	ftdi_set_interface(&ftdic, ifnum);

	if (devstr != NULL) {
		if (ftdi_usb_open_string(&ftdic, devstr)) {
			fprintf(stderr, "Can't find iCE FTDI USB device (device string %s).\n", devstr);
			error();
		}
	} else {
		if (ftdi_usb_open(&ftdic, 0x0403, 0x6010)) {
			fprintf(stderr, "Can't find iCE FTDI USB device (vedor_id 0x0403, device_id 0x6010).\n");
			error();
		}
	}

	ftdic_open = true;

	if (ftdi_usb_reset(&ftdic)) {
		fprintf(stderr, "Failed to reset iCE FTDI USB device.\n");
		error();
	}

	if (ftdi_usb_purge_buffers(&ftdic)) {
		fprintf(stderr, "Failed to purge buffers on iCE FTDI USB device.\n");
		error();
	}

        //if(ftdi_set_baudrate(&ftdic, 3000000))
        if(ftdi_set_baudrate(&ftdic, 12000000))
        {
                printf("baudrate incorrect\n");
                error();
        }

        if (ftdi_setflowctrl(&ftdic,SIO_DISABLE_FLOW_CTRL))
        {
                printf("setflowctrl error\n");
                error();
        }
        if (ftdi_setrts(&ftdic,0))
        {
                printf("setflowctrl error\n");
                error();
        }
        usleep(100);
        if (ftdi_setrts(&ftdic,1))
        {
                printf("setflowctrl error\n");
                error();
        }

        /*
        if(ftdi_set_line_property(&ftdic, BITS_8, STOP_BIT_1, NONE))
        {
                printf("line settings incorrect");
                error();
        }
        */

        /*
        if (ftdi_set_bitmode(&ftdic, 0xff, BITMODE_MPSSE) < 0) {

		fprintf(stderr, "Failed set BITMODE_MPSSE on iCE FTDI USB device.\n");
		error();
	}
        */

        //Disabling bitbang before use is apparently needed
        /*
	ftdi_disable_bitbang(&ftdic);
        if (ftdi_set_bitmode(&ftdic, 0xff, BITMODE_BITBANG)) {
		fprintf(stderr, "Failed set BITMODE on iCE FTDI USB device.\n");
		error();
	}
        */

#if 0
        size_t i;
        const size_t N = 16;
        char buffer[N];
        /*
        for(i = 0; i < N; i++){
                if (ftdi_read_data(&ftdic, (unsigned char*)(buffer + i), 1) <= 0){
                        fprintf(stderr, "Read error\n");
                        error();
                }
        }
        */
        size_t total_read = 0;
        for(;;){
                int read;
                /*
                if ((read = ftdi_read_data(&ftdic, (unsigned char*) buffer, N)) <= 0){
                        fprintf(stderr, "Read error\n");
                        error();
                }
                for(i = 0; i < N; i++){
                        if (buffer[i] > 0x02){
                                total_read++;
                                fprintf(stderr, "%c", buffer[i]);
                        }
                }
                if (total_read >= 50){
                        break;
                }
                */

                break;
        }
#endif

        if (ftdi_readstream(&ftdic, readCallback, NULL, 8, 256) <= 0){
                fprintf(stderr, "Read error\n");
                error();
        }

#if 0
	ftdi_disable_bitbang(&ftdic);
        if (ftdi_set_bitmode(&ftdic, 0xff, BITMODE_BITBANG)) {
		fprintf(stderr, "Failed set BITMODE on iCE FTDI USB device.\n");
		error();
	}

        size_t i;
        char buffer[4];
        memset(buffer, 0, sizeof(buffer));
        size_t total_read = 0;
        size_t j;
        for(j = 0; j < (1ULL << 20); j++){
                for(i = 0; i < 1; i++){
                        //Reads up to 8 pins to the buffer I think
                        if(ftdi_read_pins(&ftdic, (unsigned char*)(buffer + i))){
                                fprintf(stderr, "Couldn't get pins\n");
                                error();
                        }
                }
                /*
                for(i = 0; i < 8; i++){
                        printf("%02x", *buffer);
                }
                printf("\n");
                */
        }

#endif


#if 0
	if (ftdi_set_bitmode(&ftdic, 0xff, BITMODE_MPSSE) < 0) {
		fprintf(stderr, "Failed set BITMODE_MPSSE on iCE FTDI USB device.\n");
		error();
	}

	// enable clock divide by 5
	send_byte(0x8b);

	// set 6 MHz clock
	send_byte(0x86);
	send_byte(0x00);
	send_byte(0x00);

	fprintf(stderr, "cdone: %s\n", get_cdone() ? "high" : "low");

	set_gpio(1, 1);
	usleep(100000);

        // ---------------------------------------------------------
        // Reset
        // ---------------------------------------------------------

        fprintf(stderr, "reset..\n");

        set_gpio(1, 0);
        usleep(250000);

        fprintf(stderr, "cdone: %s\n", get_cdone() ? "high" : "low");

        flash_power_up();

        flash_read_id();


        // ---------------------------------------------------------
        // Read/Verify
        // ---------------------------------------------------------

        uint8_t buffer[256];
        flash_read(rw_offset + addr, buffer, 256);

        // ---------------------------------------------------------
        // Reset
        // ---------------------------------------------------------

        flash_power_down();

        set_gpio(1, 1);
        usleep(250000);

        fprintf(stderr, "cdone: %s\n", get_cdone() ? "high" : "low");
#endif


	// ---------------------------------------------------------
	// Exit
	// ---------------------------------------------------------

out:
	fprintf(stderr, "Bye.\n");
	ftdi_disable_bitbang(&ftdic);
	ftdi_usb_close(&ftdic);
	ftdi_deinit(&ftdic);
	return 0;
}

