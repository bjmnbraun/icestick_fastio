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
#include <libusb.h>

struct ftdi_context ftdic;
bool ftdic_open = false;

void error()
{
	//check_rx();
	fprintf(stderr, "ABORT.\n");
	if (ftdic_open)
		ftdi_usb_close(&ftdic);
	ftdi_deinit(&ftdic);
	exit(1);
}

bool exitRequested = false;

static void
sigintHandler(int signum)
{
        exitRequested = 1;
}

typedef struct
{
    void *userdata;
    int packetsize;
    int result;
    bool done;
    bool should_ack;
    FTDIProgressInfo progress;
} FTDIStreamState;

typedef struct {
        //This assumes 8bits per byte, by the way.
        unsigned char* buffer;
        //Counts how many bits have been read from buffer
        size_t i;
} bit_iter;

int pull_bits_int(bit_iter* iter, size_t nbits){
        int toRet = 0;

        //There are faster ways to do this, but whatever:
        size_t j = 0;
        for(j = 0; j < nbits; j++){
                //Convenience
                size_t i = iter->i;
                int cbit = (iter->buffer[i/8]>>(i%8))&1;
                toRet |= cbit << j;

                iter->i++;
        }

        return toRet;
}

long pull_bits_long(bit_iter* iter, size_t nbits){
        long toRet = 0;

        //There are faster ways to do this, but whatever:
        size_t j = 0;
        for(j = 0; j < nbits; j++){
                //Convenience
                size_t i = iter->i;
                int cbit = (iter->buffer[i/8]>>(i%8))&1;
                toRet |= cbit << j;

                iter->i++;
        }

        return toRet;
}

//Printf state. We read in each printf one byte at a time.
//Returns the number of bytes actually used. The tail end should be kept and
//passed in with the next buffer.
int process_printf_output(size_t* read, void* buffer, size_t size){
        //As we iterate, we increment buffer and decrement size_left
        *read = 0;
        size_t size_left = size;

        //TODO make configurable
        size_t HEADER_SIZE = 1;

        while(size_left >= HEADER_SIZE){
                //Read the header
                size_t index = ((unsigned char*)buffer)[0];
                if (index >= 4){
                        printf("Invalid printf index! %zd\n", index);
                        /*
                        //XXX
                        buffer = ((unsigned char*)buffer)+1;
                        *read+=1;
                        continue;
                        */
                        return -EINVAL;
                }

                //Look up the argument length
                const size_t lengths[] = {${PRINTF_ARGLENGTHS}};

                size_t length = lengths[index];

                if (size_left - HEADER_SIZE < length){
                        //Not enough left in buffer to read args
                        break;
                }

                //There is enough space.
                bit_iter iter = {.buffer = (unsigned char*)buffer + HEADER_SIZE};

                switch(index){
                        ${PRINTF_CASES}
                };

                size_t total_size = HEADER_SIZE + length;

                //XXX
#if 0
                {
                        size_t i;
                        for(i = 0; i < total_size; i++){
                                printf("%02x ", ((unsigned char*)buffer)[i]);
                        }
                        printf("\n");
                }
#endif
                buffer = ((char*)buffer)+total_size;
                *read+=total_size;
                size_left -= total_size;
        }
        return 0;
}

//Yuck, we maintain a packet across readstream_cb calls:
unsigned char packet[512*2];
size_t bytes_in_packet = 0;

int bufferSize = 512*8;//ftdi->max_packet_size * 8;
size_t bytes_read_no_ack = 0;

 //state->result is only set when some error happens
static void LIBUSB_CALL
ftdi_readstream_cb(struct libusb_transfer *transfer)
{
    FTDIStreamState *state = transfer->user_data;
    int packet_size = state->packetsize;
    if (transfer->status == LIBUSB_TRANSFER_COMPLETED)
    {
        int i;
        uint8_t *ptr = transfer->buffer;
        int length = transfer->actual_length;
        int res = 0;

        if (packet_size*2 != sizeof(packet)){
                printf("Assertion error\n");
                res = -EINVAL;
                goto done;
        }

        if (length <= 2){
                //printf("zero length transaction\n");
                goto done;
        }
        //ftdi puts two bytes of modem status at the start of each packet. The last packet might be incomplete.

        int numPackets = (length + packet_size - 1) / packet_size;

        for (i = 0; i < numPackets; i++)
        {
            int payloadLen;
            int packetLen = length;

            if (packetLen > packet_size)
                packetLen = packet_size;

            if (packetLen <= 2)
                break;

            //printf("Packet %d Length %d\n", i, packetLen);

            bytes_read_no_ack += packetLen;
            payloadLen = packetLen - 2;
            state->progress.current.totalBytes += payloadLen;

            //Account for bytes "carried over" from a prior packet:
            if (bytes_in_packet >= packet_size){
                printf("i Assertion error\n");
            }
            memcpy(packet + bytes_in_packet, ptr + 2, payloadLen);
            payloadLen += bytes_in_packet;
            bytes_in_packet = 0;

            size_t read;
            res = process_printf_output(&read, packet, payloadLen);
            if (res){
                //TODO we probably need to restart the stream or something
                goto done;
            }
            if (read != payloadLen){
                memcpy(
                        packet,
                        packet + read,
                        payloadLen - read
                );
                bytes_in_packet = payloadLen - read;
            }

            ptr += packetLen;
            length -= packetLen;
        }

done:
        if (res)
        {
            state->result = res;
        }
        else
        {
            state->done = true;
            state->result = 0;
            if (bytes_read_no_ack >= bufferSize){
                bytes_read_no_ack -= bufferSize;
                state->should_ack = true;
            }
        }
        return;
    } else {
        fprintf(stderr, "unknown status %d\n",transfer->status);
        state->result = LIBUSB_ERROR_IO;
    }
}

/**
   Helper function to calculate (unix) time differences

   \param a timeval
   \param b timeval
*/
static double
TimevalDiff(const struct timeval *a, const struct timeval *b)
{
    return (a->tv_sec - b->tv_sec) + 1e-6 * (a->tv_usec - b->tv_usec);
}

int my_ftdi_readstream(struct ftdi_context *ftdi)
{
        FTDIStreamState state = { NULL, ftdi->max_packet_size, 0,
false};
        //HACKS!!!
        //
        //Buffer must be a multiple of packet size
        //
        //Buffersize should be exactly the message size the FPGA program wants
        //to send. Buffersize also cannot be too large, since we need the FTDI
        //chip to respond to the buffer in a single transfer (and it seems to
        //be breaking into multiple transfers for large buffersizes.)
        //
        //While USB is a reliable transport protocol, the FTDI chip will
        //silently overwrite buffers if we allow too much to accumulate on the
        //chip's buffers. So, we use an accounting scheme where we tell the
        //FPGA after we have submitted a read request. The FPGA will use this
        //information to never run too far ahead of the stream of read
        //requests.
        //
        // (in the current implementation, the FPGA will at most work one
        // buffer ahead of the read stream)
        //
        //We read exactly this much information from the FPGA each time.
        //Though, due to the FTDI's modem bytes we actually write
        //(ftdi->max_packet_size - 2)*N bytes from the FPGA's UART
        //
        //the *8 here must match exactly the output chunk size output by the
        //FPGA program.
        int xferIndex;
        int err = 0;

        /* Only FT2232H and FT232H know about the synchronous FIFO Mode*/
        if ((ftdi->type != TYPE_2232H) && (ftdi->type != TYPE_232H))
        {
                fprintf(stderr,"Device doesn't support synchronous FIFO mode\n");
                return 1;
        }

        /* We don't know in what state we are, switch to reset*/
        if (ftdi_set_bitmode(ftdi,  0xff, BITMODE_RESET) < 0)
        {
                fprintf(stderr,"Can't reset mode\n");
                return 1;
        }

        if (ftdi_setrts(&ftdic,0))
        {
                printf("setflowctrl error\n");
                error();
        }
        //We should only need to stall here for one clock tick of the FPGA,
        //which is 1/12MHz. Probably unecessary but may as well be safe:
        usleep(1);

        /* Purge anything remaining in the buffers*/
        if (ftdi_usb_purge_buffers(ftdi) < 0)
        {
                fprintf(stderr,"Can't Purge\n");
                return 1;
        }

        //Clear reset
        if (ftdi_setrts(&ftdic,1))
        {
                printf("setflowctrl error\n");
                error();
        }

        //At this point, the FPGA is generating the first buffer. That's OK, it
        //can sit in the FTDI's buffers until we request it.

        /*
         * Set up the transfer
         */
        struct libusb_transfer *transfer;
        transfer = libusb_alloc_transfer(0);
        if (!transfer)
        {
                fprintf(stderr, "No libusb_alloc_transfer\n");
                err = LIBUSB_ERROR_NO_MEM;
                goto cleanup;
        }

        void* buffer = malloc(bufferSize);
        if (!buffer){
                fprintf(stderr, "No buffer\n");
                err = LIBUSB_ERROR_NO_MEM;
                goto cleanup;
        }

        libusb_fill_bulk_transfer(transfer, ftdi->usb_dev, ftdi->out_ep,
                        malloc(bufferSize), bufferSize,
                        ftdi_readstream_cb,
                        &state, 0);


        gettimeofday(&state.progress.first.time, NULL);
        //Copy first to prev
        state.progress.prev = state.progress.first;

        if (ftdi_setdtr(&ftdic,1))
        {
                printf("setflowctrl error\n");
                error();
        }

        bool should_ack = false;

again:
        state.result = 0;
        state.done = false;
        state.should_ack = false;
        transfer->status = -1;
        err = libusb_submit_transfer(transfer);
        if (err) {
                fprintf(stderr, "Can't submit\n");
                goto cleanup;
        }

        if (should_ack){
                //Tell the current FPGA that we have receive capacity for the current buffer
                //and one more, so it can move on to the next
                if (ftdi_setdtr(&ftdic,0))
                {
                        printf("setflowctrl error\n");
                        error();
                }
                if (ftdi_setdtr(&ftdic,1))
                {
                        printf("setflowctrl error\n");
                        error();
                }
        }
        should_ack = false;


        //TODO if we time out or otherwise error below, re-reset the device
        //with the reset bit and flushing the FTDI buffers
        do
        {
                FTDIProgressInfo  *progress = &state.progress;
                const double progressInterval = 1.0;
                struct timeval timeout = { 0, ftdi->usb_read_timeout };
                struct timeval now;

                int err = libusb_handle_events_timeout(ftdi->usb_ctx,
&timeout);
                if (err){
                        printf("Error in handle_events_timeout");
                        goto cleanup;
                }

                // If enough time has elapsed, update the progress
                gettimeofday(&now, NULL);
                double timeSincePrev = TimevalDiff(&now, &progress->prev.time);
                if (timeSincePrev >= progressInterval)
                {
                        progress->current.time = now;
                        progress->totalTime =
TimevalDiff(&progress->current.time,
                                        &progress->first.time);

                        progress->totalRate =
                                progress->current.totalBytes
/progress->totalTime;

                        progress->currentRate =
                                (progress->current.totalBytes -
                                 progress->prev.totalBytes) / timeSincePrev;

                        if (progress->currentRate){
                                printf(
                                        "Rate: %.3f\n",
                                        (progress->currentRate / (1024.0*1024.0))
                                );
                        }
                        progress->prev = progress->current;
                }
        } while (!state.result && !state.done);

        if (state.result){
                goto cleanup;
        }

        if (state.should_ack){
                should_ack = true;
        }
        goto again;

cleanup:
        //TODO proper cleanup
        if (err)
                return err;
        else
                return state.result;
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

        //Interface A is the flash channel and B is the UART channel
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

        //For printf, low latency is great!
        if (ftdi_set_latency_timer(&ftdic, 2)){
                printf("Couldn't set latency timer to 2ms\n");
                error();
        }

        //The main loop
        if (my_ftdi_readstream(&ftdic)){
                fprintf(stderr, "Read error\n");
                error();
        }

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

