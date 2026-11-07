#!/bin/sh
# Kindle: fetch the dashboard image from the Pi and draw it, every 30 s while awake.
# Location on the Kindle: /mnt/us/sensor_loop.sh  (top level of the Kindle drive)
sleep 5
lipc-set-prop com.lab126.powerd preventScreenSaver 0
FBINK=/mnt/us/libkh/bin/fbink
FAILS=0
N=0
while true; do
  STATE=$(lipc-get-prop com.lab126.powerd state 2>/dev/null)
  if [ "$STATE" = "active" ]; then
    lipc-set-prop com.lab126.powerd touchScreenSaverTimeout 1 2>/dev/null
    N=$((N+1))
    FLASH=""
    [ $((N % 10)) -eq 1 ] && FLASH="-f"
    if curl -s -f -m 15 -o /tmp/dash.png http://192.168.1.35:8080/dashboard.png; then
      FAILS=0
      $FBINK -c $FLASH -g file=/tmp/dash.png
    else
      FAILS=$((FAILS+1))
      [ $FAILS -ge 3 ] && $FBINK -c -f -S 4 -m -M "No connection"
    fi
  fi
  sleep 30
done
