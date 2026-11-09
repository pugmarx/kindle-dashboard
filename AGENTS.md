# AGENTS.md

Context for any coding agent picking up this project. Read this first, then `NOTES.md` for the current state and the idea backlog, and `README.md` for the user-facing description.

## What this is

A jailbroken Kindle Paperwhite 2 used as an always-on e-ink dashboard. A Raspberry Pi draws the whole screen as a PNG every 30 seconds; the Kindle downloads it and displays it. Almost all work happens in `pi/render.py`. The Kindle side is deliberately dumb and rarely needs changing.

## Data flow

1. ESP8266 publishes JSON to MQTT topic `environment/latest` on the Mosquitto broker running on the Pi. Shape: `{"temp": 30, "hum": 41, "light": 204, "motion": 0}`. Temperature in °C, humidity in %, light is a raw sensor value, motion is a PIR 0/1.
2. `kindle-bridge.service` (mosquitto_sub piped into a shell loop) writes the latest message to `/opt/kindle-feed/status.json`.
3. `kindle-render.service` runs `render.py`, which reads `status.json`, fetches outside data in a background thread, and writes `/opt/kindle-feed/dashboard.png` every 30 s (aligned to :00 and :30). Fetched data is cached in `/opt/kindle-feed/cache.json`.
4. `kindle-web.service` serves `/opt/kindle-feed/` with `python3 -m http.server 8080`.
5. On the Kindle, `sensor_loop.sh` curls `http://192.168.1.35:8080/dashboard.png` every 30 s while the device is awake and draws it with `/mnt/us/libkh/bin/fbink -g file=...`.

## Environment and hard constraints

Pi (192.168.1.35, user `pi`):
- Raspbian Buster, Python 3.7, an old Pillow (no `ImageDraw.rounded_rectangle`; don't rely on `anchor=` for text or `textbbox`). `render.py` has helpers (`text_size`, `text_center`, `text_right`, `wrap`, `fit`) that work on old and new Pillow; use them. Avoid f-strings only out of consistency; `.format` is used throughout.
- apt repositories for Buster are gone. Don't plan on installing new packages. Only the standard library and Pillow are available.
- DNS lookups take about 10 s and `urllib`'s timeout doesn't cover them. All network calls must stay in `update_net()`, which runs in the background `fetch_loop` thread, so the render loop never blocks.
- Fonts: Nunito from `/opt/kindle-feed/fonts/` if present, otherwise DejaVu Sans (scaled by 0.92). Layout has to fit with either.

Kindle:
- Paperwhite 2 (6th gen), firmware 5.12.2.2, jailbroken with WinterBreak2 plus the low-memory fix. KMC and shell integration are installed, so `.sh` files in `documents/` appear in the library and run as root when tapped. KUAL/MRPI are not used.
- Screen 758×1024, 212 dpi, 16 grey levels. The dashboard is designed landscape at 1024×758 and rotated with `ROTATE = 90` before saving.
- The Kindle UI (lab126_gui) is intentionally left running so the power button, cover and brightness still work. Don't stop the framework; that was tried and broke sleep and brightness. The loop checks `lipc-get-prop com.lab126.powerd state` and only draws when `active`, and pokes `touchScreenSaverTimeout` to stop auto-sleep.
- Every 10th refresh is a full flash (`-f`) to clear ghosting.

## render.py map

- Settings at the top: `LAT, LON, PLACE`, `ROTATE`, `NIGHT_FROM, NIGHT_TO`, `SHIFT`, `LIGHT_DIM, LIGHT_BRIGHT`.
- Icons are drawn with plain shape functions (`thermometer`, `droplet`, `sun`, `person`, `glass`, `stretcher`, weather `w_*`, `newspaper`, `planet`). `shaded()` draws them 4× as a mask and adds the glossy glint from the matching `gloss_*` function in `GLOSS`, or a soft glow at night. `draw_icon()` pastes with `ImageChops.darker` so the icon box never covers neighbouring text. Use `box=` and `scale=` to size them.
- Data: `update_net()` fetches Open-Meteo weather (15 min) and air quality (30 min), Hacker News top stories (hourly, stored as `cache["tech"]` with title, site, points), and NASA's news release RSS (hourly, `cache["nasa"]`). `update_today()` tracks today's min/max room temp and humidity. `moon_phase()` is computed locally.
- Layout (landscape coordinates): left half x 0–512 has `block_sensors` (2×2, y 0–380) and, below `PANEL_TOP = 384`, a panel that alternates every 180 s between `block_calendar` and `block_tech`. Right half x 540–1004 (`RX0`, `RX1`) has `block_news` with the NASA headline (y 20–205; replaced by `block_reminder` when `reminder()` returns water or stretch), `block_clock` (y 216–420), and `block_weather` (y 450–696, including AQI, sunrise/sunset and moon). Footer at y 716 shows `mood()` and the last-update time.
- `protect()` applies the hourly pixel shift and night inversion. Night icons are pre-inverted so they come out as white with a glow.

## How to work on it

Preview locally before handing anything over:

```
python3 tools/preview.py                       # day, calendar
python3 tools/preview.py --panel tech --night  # tech panel, night mode
python3 tools/preview.py --reminder stretch
```

Always look at the result, and test the widest realistic values (100% humidity, 38°, long headlines, "Waning crescent") so nothing overflows.

Deploying is done by the user: download `render.py`, `scp` it to `/tmp` on the Pi, move it to `/opt/kindle-feed/render.py`, and `sudo systemctl restart kindle-render`. Changes to the Kindle scripts need the Kindle plugged into the Mac and a stop/start from the library.

## Working with the user

- The user is on a Mac (zsh). Give short, numbered, step-by-step instructions and say which machine each command runs on. They dislike long explanations.
- Never push code to remote repositories (e.g. `git push`) without explicitly asking the user and receiving permission first.
- Prefer handing over a whole file to download over asking them to paste long code into nano. Pasting multi-line heredocs into zsh has failed before, and pasting indented code into nano broke Python indentation.
- Remind them to `rm ~/Downloads/render*.py` before downloading a new copy, because macOS renames duplicates and the old file gets deployed.
- Show a rendered preview of visual changes. They care about the look: flat black clipart-style icons with a small white glint, rounded font, balanced layout, readable from 3–4 ft away (avoid light grey text for anything that matters).
- They decide scope. Propose, then build once they agree, and keep the dashboard working at every step.
