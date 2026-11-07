# Notes

Things worth remembering when I pick this up again.

## Current state

Everything in this repo is what's running. The Pi side is installed at `/opt/kindle-feed/`, and the Kindle scripts sit on the Kindle as described in the README. To update the dashboard I copy a new `render.py` to the Pi with `scp` and restart `kindle-render`. The Kindle doesn't need touching for layout changes.

The screen is laid out landscape at 1024×758 and rotated before saving. The left half has the four sensor readings on top and a panel below that swaps between the month calendar and tech news every three minutes. The right half has a NASA headline at the top (replaced by a water or stretch reminder when one is due), a big clock and date in the middle, and the weather panel at the bottom with AQI, sunrise, sunset and the moon. The footer has a one-line comment about the room and the time of the last sensor update.

## Quirks

The Pi runs Raspbian Buster. Its apt repositories are gone, so installing new packages doesn't work without pointing apt at the legacy archive. Its DNS lookups also take about ten seconds, which is why all internet fetching happens in a background thread. A slow or hanging service never holds up the dashboard.

The Pi has an old Pillow, so `rounded_rectangle` and some newer text functions aren't available. `render.py` works around this.

When downloading a new `render.py` on the Mac, delete old copies first. Otherwise macOS saves it as `render (1).py` and the old file gets copied by mistake.

To test night mode during the day, set `NIGHT_FROM, NIGHT_TO = 0, 24`, restart, look, and set it back to `21, 7`.

## Sensors

The light sensor sits next to a desk lamp on the monitor, so it mostly sees the lamp turning on and off rather than daylight. The Dark/Dim/Bright thresholds are guesses until I note down real readings.

The PIR motion sensor isn't reliable, so presence only shows Here or Empty. If I add a better sensor like LiDAR, it would be nice to show when someone was last seen.

## Ideas for later

- A Pomodoro timer, started from a physical button on the ESP8266 or a small web page on the Pi, with the countdown drawn on the dashboard.
- QR codes next to headlines so I can open the article on my phone.
- Real touch zones on the Kindle. This needs a small program that reads taps, and probably pausing the Kindle interface while it runs.
- Keeping the Kindle's status bar visible permanently by drawing the dashboard below it (`fbink -g file=...,y=70` and cropping the top of the image on the Pi).
- Treating the light reading as "desk lamp on/off" instead of a room light level.
