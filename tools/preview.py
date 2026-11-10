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
    "tech": [
        {"title": "Meet *sshole, the vulnerability that lets hackers SSH into Linux devices",
         "url": "https://arstechnica.com/security/2026/11/vulnerability-allows-attackers-to-log-into-some-linux-devices-sans-password/",
         "source": "Ars Technica",
         "site": "arstechnica.com",
         "summary": "Certain default configurations of Alpine Linux and related lightweight distributions allow attackers on the local network to gain unauthorized SSH shell access without a password."},
        {"title": "Uber launches parking reservation service following SpotHero acquisition",
         "url": "https://techcrunch.com/2026/11/08/uber-launches-parking-service-following-spothero-acquisition/",
         "source": "TechCrunch",
         "site": "techcrunch.com",
         "summary": "The new feature integrates city garage and curbside parking reservation directly inside the Uber app, laying foundational infrastructure for future robotaxi dropoff stations."},
        {"title": "Chainalysis says hackers stole credentials and API tokens for all customers",
         "url": "https://arstechnica.com/security/2026/11/chainalysis-says-hackers-stole-credentials-and-tokens-for-all-of-its-customers/",
         "source": "Ars Technica",
         "site": "arstechnica.com",
         "summary": "The blockchain analytics firm confirmed a multifront cyberattack that compromised customer service portals and internal monitoring tokens across its global client base."}],
    "ai_news": [
        {"title": "Anthropic debuts Claude 3.7 Sonnet with hybrid reasoning architecture",
         "url": "https://arstechnica.com/ai/2026/02/anthropic-claude-3-7-sonnet/",
         "source": "Ars Technica",
         "summary": "The new frontier model combines rapid standard token generation with configurable test-time thinking. Developers can dynamically set thinking budgets to balance latency and complex reasoning depth."},
        {"title": "OpenAI releases open-weights model family targeting local agent execution",
         "url": "https://venturebeat.com/ai/openai-open-weights-agent-models/",
         "source": "VentureBeat",
         "summary": "Designed specifically for offline edge inference and private enterprise workflows, the Apache-2.0 licensed models match GPT-4o mini on tool use benchmarks while running comfortably on consumer GPUs."},
        {"title": "DeepSeek unveils sparse mixture-of-experts update reducing training costs by 60%",
         "url": "https://arstechnica.com/ai/2026/02/deepseek-v3-moe-architecture/",
         "source": "Ars Technica",
         "summary": "By decoupling attention heads and implementing multi-token prediction loss, researchers achieved state-of-the-art coding and math scores with dramatically lower cluster compute requirements."}
    ],
    "today": {"day": time.strftime("%Y-%m-%d"), "temp_lo": 26.4, "temp_hi": 31.2,
              "hum_lo": 38, "hum_hi": 44},
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--view", choices=["dash", "tech", "ai"], default="dash")
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
    cache = dict(SAMPLE_CACHE)
    cache["view"] = a.view
    cache["view_time"] = real()
    try:
        img = R.protect(R.render(cache))
    finally:
        R.time.time = real
    img.save(a.out)
    print("wrote", a.out)

if __name__ == "__main__":
    main()
