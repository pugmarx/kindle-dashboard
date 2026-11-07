#!/bin/sh
# Kindle: "off" button. Location: /mnt/us/documents/sensor_stop.sh
pkill -f sensor_loop.sh
lipc-set-prop com.lab126.powerd preventScreenSaver 0
