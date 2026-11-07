#!/usr/bin/env python3
"""Render the dashboard locally with sample data, without a Pi or Kindle.

    python3 tools/preview.py                    # day mode, calendar panel
    python3 tools/preview.py --panel tech       # tech news in the bottom-left
    python3 tools/preview.py --night            # inverted night look
    python3 tools/preview.py --reminder water   # or: stretch
    python3 tools/preview.py --out /tmp/x.png

The output is the landscape image before rotation, so it's easy to look at.
Needs Pillow. Uses DejaVu fonts if Nunito isn't installed.
"""
import argparse, json, os, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "pi"))
import render as R  # noqa: E402

SAMPLE_STATUS = {"temp": 29, "hum": 41, "light": 204, "motion": 0}
SAMPLE_CACHE = {
    "weather": {"temp": 24.3, "hum": 55, "code": 2, "feels": 26.1, "hi": 31.2,
                "lo": 19.8, "rain": 20, "sunrise": "06:32", "sunset": "17:58"},
    "air": {"aqi": 87, "pm25": 31},
    "nasa": ["NASA Selects New Instruments for Future Mission to Study Earth's Changing Climate"],
    "tech": [{"title": "Show HN: A tiny e-ink dashboard for your home sensors",
              "site": "github.com", "points": 412},
             {"title": "SQLite is not a toy database", "site": "antonz.org", "points": 231}],
    "today": {"day": time.strftime("%Y-%m-%d"), "temp_lo": 26.4, "temp_hi": 31.2,
              "hum_lo": 38, "hum_hi": 44},
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", choices=["calendar", "tech"], default="calendar")
    ap.add_argument("--night", action="store_true")
    ap.add_argument("--reminder", choices=["water", "stretch"])
    ap.add_argument("--status", help="JSON for the sensor reading, e.g. '{\"temp\": 31}'")
    ap.add_argument("--out", default="preview.png")
    a = ap.parse_args()

    tmp = tempfile.mkdtemp()
    R.SRC = os.path.join(tmp, "status.json")
    with open(R.SRC, "w") as f:
        json.dump(json.loads(a.status) if a.status else SAMPLE_STATUS, f)

    R.reminder = lambda: a.reminder
    if a.night:
        R.NIGHT_FROM, R.NIGHT_TO = 0, 24
    else:
        R.NIGHT_FROM, R.NIGHT_TO = 24, 0

    # the bottom-left panel switches every 3 minutes; pin the clock to the one we want
    real = time.time
    base = (int(real()) // 360) * 360
    R.time.time = lambda: base + (190 if a.panel == "tech" else 10)
    try:
        img = R.protect(R.render(dict(SAMPLE_CACHE)))
    finally:
        R.time.time = real
    img.save(a.out)
    print("wrote", a.out)

if __name__ == "__main__":
    main()
