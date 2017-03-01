#!/bin/bash

#The name of the device might not be USB1 if you've plugged it in multiple
#times, FIXME
#sudo stty -F /dev/ttyUSB1 115200 raw
sudo stty -F /dev/ttyUSB1 ispeed 3000000 ospeed 3000000 raw
sudo head /dev/ttyUSB1
#This should just keep going
sudo cat /dev/ttyUSB1 > /dev/null
