#!/bin/sh
# Kindle: "on" button. Location: /mnt/us/documents/sensor_start.sh
nohup sh /mnt/us/sensor_loop.sh > /mnt/us/sensor.log 2>&1 &
