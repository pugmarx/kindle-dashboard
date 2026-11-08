#!/usr/bin/env python3
"""Generate high-resolution PNG schematics for the Kindle Environment Monitor setup:
1. docs/system-architecture.png - Overall system architecture & data pipeline
2. docs/arduino-schematic.png    - Detailed Arduino & sensor hardware wiring
"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, "..", "docs")
os.makedirs(DOCS, exist_ok=True)

# Fonts
def get_font(bold=False, size=18):
    names = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/lato/Lato-Bold.ttf" if bold else "/usr/share/fonts/truetype/lato/Lato-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else "/usr/share/fonts/truetype/freefont/FreeSans.ttf"
    ]
    for path in names:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()

def draw_arrow(d, p1, p2, fill=(71, 85, 105), width=3, arrow_size=10):
    """Draw a directed line with an arrowhead from p1 to p2."""
    d.line([p1, p2], fill=fill, width=width)
    x1, y1 = p1
    x2, y2 = p2
    import math
    angle = math.atan2(y2 - y1, x2 - x1)
    # Arrowhead points
    a1 = (x2 - arrow_size * math.cos(angle - math.pi / 6),
          y2 - arrow_size * math.sin(angle - math.pi / 6))
    a2 = (x2 - arrow_size * math.cos(angle + math.pi / 6),
          y2 - arrow_size * math.sin(angle + math.pi / 6))
    d.polygon([p2, a1, a2], fill=fill)

def draw_box(d, bbox, fill=(255, 255, 255), outline=(203, 213, 225), radius=12, width=2):
    """Draw a rounded rectangle with fill and outline."""
    x0, y0, x1, y1 = bbox
    r = radius
    # Body
    d.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
    d.rectangle([x0, y0 + r, x1, y1 - r], fill=fill)
    # Corners
    d.pieslice([x0, y0, x0 + 2*r, y0 + 2*r], 180, 270, fill=fill)
    d.pieslice([x1 - 2*r, y0, x1, y0 + 2*r], 270, 360, fill=fill)
    d.pieslice([x0, y1 - 2*r, x0 + 2*r, y1], 90, 180, fill=fill)
    d.pieslice([x1 - 2*r, y1 - 2*r, x1, y1], 0, 90, fill=fill)
    # Outlines
    d.line([x0 + r, y0, x1 - r, y0], fill=outline, width=width)
    d.line([x0 + r, y1, x1 - r, y1], fill=outline, width=width)
    d.line([x0, y0 + r, x0, y1 - r], fill=outline, width=width)
    d.line([x1, y0 + r, x1, y1 - r], fill=outline, width=width)
    d.arc([x0, y0, x0 + 2*r, y0 + 2*r], 180, 270, fill=outline, width=width)
    d.arc([x1 - 2*r, y0, x1, y0 + 2*r], 270, 360, fill=outline, width=width)
    d.arc([x0, y1 - 2*r, x0 + 2*r, y1], 90, 180, fill=outline, width=width)
    d.arc([x1 - 2*r, y1 - 2*r, x1, y1], 0, 90, fill=outline, width=width)

# =========================================================================
# 1. OVERALL SYSTEM ARCHITECTURE SCHEMATIC
# =========================================================================
def generate_system_architecture():
    W, H = 1920, 1080
    img = Image.new("RGB", (W, H), (248, 250, 252)) # Slate 50
    d = ImageDraw.Draw(img)

    f_title = get_font(True, 36)
    f_sub = get_font(False, 20)
    f_header = get_font(True, 24)
    f_body_b = get_font(True, 18)
    f_body = get_font(False, 17)
    f_mono = get_font(True, 15)
    f_small = get_font(False, 15)

    # Title Bar
    d.text((60, 40), "Kindle Environment Monitor — System Architecture & Data Pipeline", font=f_title, fill=(15, 23, 42))
    d.text((60, 88), "End-to-end telemetry, event routing, background rendering and e-ink display cycle", font=f_sub, fill=(100, 116, 139))
    d.line([60, 125, W - 60, 125], fill=(226, 232, 240), width=2)

    # 3 Main Tier Columns
    # Tier 1: Hardware & Sensing Tier (Arduino)
    # Tier 2: Processing & Integration Tier (Raspberry Pi)
    # Tier 3: Display & Client Tier (Kindle Paperwhite)
    
    col_w = 540
    y_top = 150
    y_bot = 1000

    # Column 1 Background (Arduino)
    draw_box(d, [60, y_top, 60 + col_w, y_bot], fill=(255, 255, 255), outline=(203, 213, 225), radius=16)
    d.rectangle([60, y_top, 60 + col_w, y_top + 60], fill=(241, 245, 249))
    d.text((85, y_top + 16), "1. SENSING TIER · ARDUINO", font=f_header, fill=(30, 41, 59))
    d.text((85, y_top + 42), "Hardware telemetry & tactile input", font=f_small, fill=(100, 116, 139))
    d.line([60, y_top + 68, 60 + col_w, y_top + 68], fill=(226, 232, 240), width=2)

    # Arduino Sensor Cards inside Column 1
    sensors = [
        ("DHT11 Sensor", "Pin 4 (Digital)", "Temperature & Humidity (every 2s)", (59, 130, 246)),
        ("PIR Motion Sensor", "Pin 2 (Digital)", "Presence / Motion (1 = Here, 0 = Empty)", (234, 88, 12)),
        ("LDR Light Sensor", "Pin A0 (Analog)", "Room illumination (1023 - raw level)", (202, 138, 4)),
        ("Tactile Push Button", "Pin 13 & GND", "INPUT_PULLUP (Active LOW) · Event Trigger", (147, 51, 234))
    ]
    sy = y_top + 90
    for name, pin, desc, col in sensors:
        draw_box(d, [90, sy, 570, sy + 88], fill=(248, 250, 252), outline=(226, 232, 240), radius=10)
        d.rectangle([90, sy, 98, sy + 88], fill=col)
        d.text((115, sy + 14), name, font=f_body_b, fill=(15, 23, 42))
        d.text((115, sy + 38), "GPIO: " + pin, font=f_mono, fill=col)
        d.text((115, sy + 60), desc, font=f_small, fill=(100, 116, 139))
        sy += 105

    # Serial Transmission Box
    sy += 15
    draw_box(d, [90, sy, 570, sy + 160], fill=(240, 253, 250), outline=(94, 234, 212), radius=10)
    d.text((115, sy + 15), "USB Serial Stream (/dev/ttyACM0 @ 9600)", font=f_body_b, fill=(15, 118, 110))
    d.text((115, sy + 42), "Emits JSON line every 2 seconds:", font=f_small, fill=(71, 85, 105))
    code_snippet = (
        '{\n'
        '  "temp": 28.5,  "humidity": 44.0,\n'
        '  "light": 185,  "motion": 1,\n'
        '  "button": 1    // transient event\n'
        '}'
    )
    d.text((115, sy + 65), code_snippet, font=f_mono, fill=(15, 23, 42))

    # Connection: Column 1 to Column 2
    # Arrow from Serial box to Pi
    draw_arrow(d, (570, sy + 80), (680, sy + 80), fill=(13, 148, 136), width=4, arrow_size=12)
    d.text((585, sy + 55), "USB Cable", font=f_mono, fill=(13, 148, 136))

    # Column 2 Background (Raspberry Pi)
    c2_x = 680
    draw_box(d, [c2_x, y_top, c2_x + col_w + 40, y_bot], fill=(255, 255, 255), outline=(203, 213, 225), radius=16)
    d.rectangle([c2_x, y_top, c2_x + col_w + 40, y_top + 60], fill=(241, 245, 249))
    d.text((c2_x + 25, y_top + 16), "2. PROCESSING TIER · RASPBERRY PI", font=f_header, fill=(30, 41, 59))
    d.text((c2_x + 25, y_top + 42), "Systemd services, InfluxDB, Mosquitto & Pillow render", font=f_small, fill=(100, 116, 139))
    d.line([c2_x, y_top + 68, c2_x + col_w + 40, y_top + 68], fill=(226, 232, 240), width=2)

    # Pi Components inside Column 2
    py = y_top + 85

    # 1. serial_to_influx service
    draw_box(d, [c2_x + 25, py, c2_x + col_w + 15, py + 115], fill=(248, 250, 252), outline=(203, 213, 225), radius=10)
    d.text((c2_x + 45, py + 12), "serial_to_influx.service (persist_sensor_data.py)", font=f_body_b, fill=(15, 23, 42))
    d.text((c2_x + 45, py + 38), "• Reads /dev/ttyACM0 with auto-reconnecting serial", font=f_small, fill=(51, 65, 85))
    d.text((c2_x + 45, py + 62), "• If button == 1: publishes instantly to MQTT 'environment/button'", font=f_mono, fill=(147, 51, 234))
    d.text((c2_x + 45, py + 86), "• Writes temp, hum, light, motion points to InfluxDB", font=f_small, fill=(51, 65, 85))

    # Split flow arrows below serial_to_influx
    # Left branch -> InfluxDB
    # Right branch -> MQTT Broker
    py += 135
    # InfluxDB Box
    draw_box(d, [c2_x + 25, py, c2_x + 255, py + 95], fill=(240, 249, 255), outline=(186, 230, 253), radius=10)
    d.text((c2_x + 40, py + 12), "InfluxDB (port 8086)", font=f_body_b, fill=(3, 105, 161))
    d.text((c2_x + 40, py + 38), "Database: 'sensors'", font=f_small, fill=(14, 116, 144))
    d.text((c2_x + 40, py + 60), "Series: environment_tagged", font=f_small, fill=(14, 116, 144))

    # Mosquitto Broker Box
    draw_box(d, [c2_x + 285, py, c2_x + col_w + 15, py + 95], fill=(254, 243, 199), outline=(252, 211, 77), radius=10)
    d.text((c2_x + 300, py + 12), "Mosquitto MQTT (1883)", font=f_body_b, fill=(180, 83, 9))
    d.text((c2_x + 300, py + 38), "Topic: environment/button", font=f_mono, fill=(180, 83, 9))
    d.text((c2_x + 300, py + 60), "Topic: environment/latest", font=f_mono, fill=(180, 83, 9))

    draw_arrow(d, (c2_x + 140, py - 20), (c2_x + 140, py), fill=(14, 116, 144), width=3)
    draw_arrow(d, (c2_x + 430, py - 20), (c2_x + 430, py), fill=(180, 83, 9), width=3)

    py += 115
    # push_to_mqtt + kindle-bridge
    draw_box(d, [c2_x + 25, py, c2_x + col_w + 15, py + 85], fill=(248, 250, 252), outline=(203, 213, 225), radius=10)
    d.text((c2_x + 45, py + 12), "push_to_mqtt.service & kindle-bridge.service", font=f_body_b, fill=(15, 23, 42))
    d.text((c2_x + 45, py + 36), "• push_to_mqtt: polls InfluxDB (every 5s) -> publishes environment/latest", font=f_small, fill=(71, 85, 105))
    d.text((c2_x + 45, py + 58), "• kindle-bridge: mosquitto_sub -> writes /opt/kindle-feed/status.json", font=f_small, fill=(71, 85, 105))

    py += 105
    # External APIs Box (Open-Meteo, Hacker News, Ars Technica)
    draw_box(d, [c2_x + 25, py, c2_x + col_w + 15, py + 85], fill=(245, 243, 255), outline=(221, 214, 254), radius=10)
    d.text((c2_x + 45, py + 12), "External Web APIs (Background Thread)", font=f_body_b, fill=(109, 40, 217))
    d.text((c2_x + 45, py + 36), "• Open-Meteo: 15-min weather forecast & 30-min AQI", font=f_small, fill=(109, 40, 217))
    d.text((c2_x + 45, py + 58), "• Hacker News Top Stories & Ars Technica AI News feed", font=f_small, fill=(109, 40, 217))

    py += 105
    # kindle-render.service (render.py)
    draw_box(d, [c2_x + 25, py, c2_x + col_w + 15, py + 160], fill=(240, 253, 244), outline=(134, 239, 172), radius=12, width=2)
    d.text((c2_x + 45, py + 14), "kindle-render.service (render.py)", font=f_body_b, fill=(21, 128, 61))
    d.text((c2_x + 45, py + 40), "• Subscribes to 'environment/button' via MQTT background loop", font=f_small, fill=(21, 128, 61))
    d.text((c2_x + 45, py + 64), "• Button Cycle: Main Dashboard <-> Tech News <-> AI Digest", font=f_body_b, fill=(15, 23, 42))
    d.text((c2_x + 45, py + 90), "• Generates 150x150 QR codes on demand with qrcode/Pillow", font=f_small, fill=(51, 65, 85))
    d.text((c2_x + 45, py + 114), "• Writes /opt/kindle-feed/dashboard.png (rotated 90 deg)", font=f_mono, fill=(15, 23, 42))
    d.text((c2_x + 45, py + 136), "• Served via HTTP on port 8080 (kindle-web.service)", font=f_small, fill=(100, 116, 139))

    # Connection: Column 2 to Column 3 (Wi-Fi)
    c3_x = 1320
    draw_arrow(d, (c2_x + col_w + 15, py + 80), (c3_x, py + 80), fill=(21, 128, 61), width=4, arrow_size=12)
    d.text((c2_x + col_w + 35, py + 50), "Wi-Fi (HTTP 8080)", font=f_mono, fill=(21, 128, 61))

    # Column 3 Background (Kindle Paperwhite)
    draw_box(d, [c3_x, y_top, c3_x + col_w, y_bot], fill=(255, 255, 255), outline=(203, 213, 225), radius=16)
    d.rectangle([c3_x, y_top, c3_x + col_w, y_top + 60], fill=(241, 245, 249))
    d.text((c3_x + 25, y_top + 16), "3. DISPLAY TIER · KINDLE PAPERWHITE", font=f_header, fill=(30, 41, 59))
    d.text((c3_x + 25, y_top + 42), "Jailbroken Paperwhite 2 · 758x1024 e-ink screen", font=f_small, fill=(100, 116, 139))
    d.line([c3_x, y_top + 68, c3_x + col_w, y_top + 68], fill=(226, 232, 240), width=2)

    # Kindle Components inside Column 3
    ky = y_top + 90
    draw_box(d, [c3_x + 25, ky, c3_x + col_w - 25, ky + 130], fill=(248, 250, 252), outline=(203, 213, 225), radius=10)
    d.text((c3_x + 45, ky + 15), "sensor_loop.sh (/mnt/us/sensor_loop.sh)", font=f_body_b, fill=(15, 23, 42))
    d.text((c3_x + 45, ky + 42), "• Runs continuously while Kindle UI is awake", font=f_small, fill=(51, 65, 85))
    d.text((c3_x + 45, ky + 66), "• Checks powerd state (sleeps when cover is closed)", font=f_small, fill=(51, 65, 85))
    d.text((c3_x + 45, ky + 90), "• curls http://192.168.1.35:8080/dashboard.png every 30s", font=f_mono, fill=(15, 23, 42))

    ky += 150
    draw_box(d, [c3_x + 25, ky, c3_x + col_w - 25, ky + 105], fill=(248, 250, 252), outline=(203, 213, 225), radius=10)
    d.text((c3_x + 45, ky + 15), "FBInk Screen Driver (/mnt/us/libkh/bin/fbink)", font=f_body_b, fill=(15, 23, 42))
    d.text((c3_x + 45, ky + 42), "• Draws image straight to e-ink frame buffer", font=f_small, fill=(51, 65, 85))
    d.text((c3_x + 45, ky + 66), "• Full screen flash (-f) every 10th refresh to clear ghosting", font=f_small, fill=(51, 65, 85))

    ky += 125
    # The 3 Switchable Screen Modes Box
    draw_box(d, [c3_x + 25, ky, c3_x + col_w - 25, ky + 250], fill=(241, 245, 249), outline=(203, 213, 225), radius=10)
    d.text((c3_x + 45, ky + 15), "Button-Switchable Screen Views:", font=f_body_b, fill=(15, 23, 42))

    views = [
        ("View 1: Main Dashboard", "Sensors (temp/hum/light/motion), Clock, Weather, Moon, Calendar"),
        ("View 2: Tech News Reader", "Top 3 Hacker News stories with direct-article QR codes on right"),
        ("View 3: AI Digest Reader", "Top 3 AI stories with rich context paragraphs + QR codes on right")
    ]
    vy = ky + 45
    for vname, vdesc in views:
        draw_box(d, [c3_x + 40, vy, c3_x + col_w - 40, vy + 55], fill=(255, 255, 255), outline=(226, 232, 240), radius=6)
        d.text((c3_x + 55, vy + 8), vname, font=f_body_b, fill=(30, 41, 59))
        d.text((c3_x + 55, vy + 30), vdesc, font=f_small, fill=(100, 116, 139))
        vy += 65

    # Footer note
    d.text((60, 1025), "Auto-timeout: If left on Tech News or AI Digest, dashboard automatically returns to View 1 after 5 minutes.", font=f_sub, fill=(100, 116, 139))

    out_path = os.path.join(DOCS, "system-architecture.png")
    img.save(out_path)
    print("Saved", out_path)

# =========================================================================
# 2. ARDUINO HARDWARE WIRING SCHEMATIC
# =========================================================================
def generate_arduino_schematic():
    W, H = 1920, 1080
    img = Image.new("RGB", (W, H), (248, 250, 252))
    d = ImageDraw.Draw(img)

    f_title = get_font(True, 36)
    f_sub = get_font(False, 20)
    f_header = get_font(True, 24)
    f_body_b = get_font(True, 18)
    f_body = get_font(False, 17)
    f_mono = get_font(True, 16)
    f_small = get_font(False, 15)

    # Title Bar
    d.text((60, 40), "Arduino Hardware & Sensor Wiring Schematic", font=f_title, fill=(15, 23, 42))
    d.text((60, 88), "Physical connections for DHT11, PIR Motion, LDR Voltage Divider, and Tactile Push Button", font=f_sub, fill=(100, 116, 139))
    d.line([60, 125, W - 60, 125], fill=(226, 232, 240), width=2)

    # Center: Arduino Board Representation
    # Left: Sensors
    # Right: Pinout Table & Wire Color Legend
    
    # 1. Arduino Uno / Nano Box in Center
    ax0, ay0, ax1, ay1 = 700, 180, 1160, 960
    draw_box(d, [ax0, ay0, ax1, ay1], fill=(255, 255, 255), outline=(15, 118, 110), radius=16, width=3)
    d.rectangle([ax0, ay0, ax1, ay0 + 65], fill=(204, 251, 241))
    d.text((ax0 + 100, ay0 + 20), "ARDUINO BOARD", font=f_header, fill=(15, 118, 110))

    # Power Rails Box on Arduino
    draw_box(d, [ax0 + 30, ay0 + 90, ax1 - 30, ay0 + 230], fill=(248, 250, 252), outline=(226, 232, 240), radius=10)
    d.text((ax0 + 50, ay0 + 105), "POWER BUS", font=f_body_b, fill=(71, 85, 105))
    
    # 5V pin, GND pin, 3.3V pin
    d.rectangle([ax0 + 50, ay0 + 140, ax0 + 120, ay0 + 190], fill=(239, 68, 68))
    d.text((ax0 + 65, ay0 + 155), "5V", font=f_body_b, fill=(255, 255, 255))
    
    d.rectangle([ax0 + 150, ay0 + 140, ax0 + 220, ay0 + 190], fill=(15, 23, 42))
    d.text((ax0 + 160, ay0 + 155), "GND", font=f_body_b, fill=(255, 255, 255))

    d.rectangle([ax0 + 250, ay0 + 140, ax0 + 330, ay0 + 190], fill=(245, 158, 11))
    d.text((ax0 + 265, ay0 + 155), "3.3V", font=f_body_b, fill=(255, 255, 255))

    # Pin Header on Arduino
    py_pins = ay0 + 260
    draw_box(d, [ax0 + 30, py_pins, ax1 - 30, ay1 - 100], fill=(248, 250, 252), outline=(226, 232, 240), radius=10)
    d.text((ax0 + 50, py_pins + 15), "I/O PINS USED", font=f_body_b, fill=(71, 85, 105))

    pins_info = [
        ("Pin 2 (PIR)", "Digital Input", (234, 88, 12), py_pins + 55),
        ("Pin 4 (DHT11)", "Digital I/O", (59, 130, 246), py_pins + 125),
        ("Pin 13 (Button)", "INPUT_PULLUP", (147, 51, 234), py_pins + 195),
        ("Pin A0 (LDR)", "Analog In (0-1023)", (202, 138, 4), py_pins + 265)
    ]
    for pname, ptype, pcol, py_pos in pins_info:
        draw_box(d, [ax0 + 50, py_pos, ax1 - 50, py_pos + 50], fill=(255, 255, 255), outline=pcol, radius=8, width=2)
        d.text((ax0 + 70, py_pos + 12), pname, font=f_body_b, fill=(15, 23, 42))
        d.text((ax0 + 240, py_pos + 15), ptype, font=f_mono, fill=pcol)

    # USB Connector at bottom of Arduino
    draw_box(d, [ax0 + 120, ay1 - 70, ax1 - 120, ay1 - 15], fill=(30, 41, 59), outline=(15, 23, 42), radius=8)
    d.text((ax0 + 140, ay1 - 52), "USB to Raspberry Pi", font=f_mono, fill=(255, 255, 255))

    # 2. Individual Component Boxes on the Left
    comp_w = 480
    
    # Component 1: DHT11
    c1_y = 180
    draw_box(d, [80, c1_y, 80 + comp_w, c1_y + 160], fill=(255, 255, 255), outline=(59, 130, 246), radius=12, width=2)
    d.text((105, c1_y + 15), "DHT11 Temp & Humidity Sensor", font=f_header, fill=(59, 130, 246))
    d.text((105, c1_y + 48), "• Pin 1 (VCC)  --> Arduino 5V", font=f_body, fill=(239, 68, 68))
    d.text((105, c1_y + 75), "• Pin 2 (DATA) --> Arduino Pin 4 (DHTPIN)", font=f_body, fill=(59, 130, 246))
    d.text((105, c1_y + 102), "• Pin 4 (GND)  --> Arduino GND", font=f_body, fill=(15, 23, 42))
    d.text((105, c1_y + 128), "Reads every 2000 ms (temp in °C, hum in %)", font=f_small, fill=(100, 116, 139))
    draw_arrow(d, (80 + comp_w, c1_y + 80), (ax0 + 50, py_pins + 150), fill=(59, 130, 246), width=3)

    # Component 2: PIR Motion Sensor
    c2_y = 370
    draw_box(d, [80, c2_y, 80 + comp_w, c2_y + 160], fill=(255, 255, 255), outline=(234, 88, 12), radius=12, width=2)
    d.text((105, c2_y + 15), "PIR Motion Sensor (HC-SR501)", font=f_header, fill=(234, 88, 12))
    d.text((105, c2_y + 48), "• VCC (5V)     --> Arduino 5V", font=f_body, fill=(239, 68, 68))
    d.text((105, c2_y + 75), "• OUT (Signal) --> Arduino Pin 2 (PIR_PIN)", font=f_body, fill=(234, 88, 12))
    d.text((105, c2_y + 102), "• GND          --> Arduino GND", font=f_body, fill=(15, 23, 42))
    d.text((105, c2_y + 128), "Digital HIGH when motion detected (Here / Empty)", font=f_small, fill=(100, 116, 139))
    draw_arrow(d, (80 + comp_w, c2_y + 80), (ax0 + 50, py_pins + 80), fill=(234, 88, 12), width=3)

    # Component 3: Tactile Push Button
    c3_y = 560
    draw_box(d, [80, c3_y, 80 + comp_w, c3_y + 180], fill=(255, 255, 255), outline=(147, 51, 234), radius=12, width=2)
    d.text((105, c3_y + 15), "Tactile Push Button (Mode Toggle)", font=f_header, fill=(147, 51, 234))
    d.text((105, c3_y + 48), "• Leg 1        --> Arduino Pin 13", font=f_body, fill=(147, 51, 234))
    d.text((105, c3_y + 75), "• Leg 2 (adjacent) --> Arduino GND", font=f_body, fill=(15, 23, 42))
    d.text((105, c3_y + 105), "Wiring: Connected between Pin 13 and adjacent GND.", font=f_small, fill=(71, 85, 105))
    d.text((105, c3_y + 128), "Mode: pinMode(13, INPUT_PULLUP) - no resistor needed!", font=f_mono, fill=(147, 51, 234))
    d.text((105, c3_y + 150), "State: Idle = HIGH (1), Pressed = LOW (0)", font=f_small, fill=(100, 116, 139))
    draw_arrow(d, (80 + comp_w, c3_y + 75), (ax0 + 50, py_pins + 220), fill=(147, 51, 234), width=3)

    # Component 4: LDR Light Sensor Divider
    c4_y = 770
    draw_box(d, [80, c4_y, 80 + comp_w, c4_y + 190], fill=(255, 255, 255), outline=(202, 138, 4), radius=12, width=2)
    d.text((105, c4_y + 15), "LDR Sensor (Voltage Divider)", font=f_header, fill=(202, 138, 4))
    d.text((105, c4_y + 48), "• 5V Rail      --> LDR leg 1", font=f_body, fill=(239, 68, 68))
    d.text((105, c4_y + 75), "• Divider Node --> Arduino Pin A0 & 10kΩ resistor", font=f_body, fill=(202, 138, 4))
    d.text((105, c4_y + 102), "• 10kΩ Resistor --> Arduino GND", font=f_body, fill=(15, 23, 42))
    d.text((105, c4_y + 132), "Calculates: light_level = 1023 - analogRead(A0)", font=f_mono, fill=(202, 138, 4))
    d.text((105, c4_y + 156), "Output: Level 0-1023 (Dark / Dim / Bright thresholds)", font=f_small, fill=(100, 116, 139))
    draw_arrow(d, (80 + comp_w, c4_y + 75), (ax0 + 50, py_pins + 290), fill=(202, 138, 4), width=3)

    # 3. Right Side: Technical Specs & Wire Legend
    rx0 = 1260
    rw = 580
    
    # Legend Box
    draw_box(d, [rx0, 180, rx0 + rw, 380], fill=(255, 255, 255), outline=(203, 213, 225), radius=12)
    d.text((rx0 + 25, 200), "WIRE COLOR CONVENTIONS", font=f_header, fill=(15, 23, 42))
    
    wires = [
        ("Red Wire", "5V Power Supply to Sensors", (239, 68, 68)),
        ("Black Wire", "Common Ground (GND) Return Rail", (15, 23, 42)),
        ("Blue Wire", "DHT11 Digital Serial Data Signal (Pin 4)", (59, 130, 246)),
        ("Orange Wire", "PIR Motion Digital Pulse Output (Pin 2)", (234, 88, 12)),
        ("Purple Wire", "Tactile Button to Pin 13 (Active LOW)", (147, 51, 234)),
        ("Amber Wire", "LDR Voltage Divider Analog Signal (Pin A0)", (202, 138, 4))
    ]
    wy = 240
    for wname, wdesc, wcol in wires:
        d.line([rx0 + 25, wy + 8, rx0 + 60, wy + 8], fill=wcol, width=4)
        d.text((rx0 + 75, wy), wname, font=f_body_b, fill=wcol)
        d.text((rx0 + 195, wy + 2), wdesc, font=f_small, fill=(71, 85, 105))
        wy += 22

    # Arduino Sketch Summary Box
    draw_box(d, [rx0, 410, rx0 + rw, 710], fill=(255, 255, 255), outline=(203, 213, 225), radius=12)
    d.text((rx0 + 25, 430), "ARDUINO SKETCH HIGHLIGHTS", font=f_header, fill=(15, 23, 42))

    notes = [
        ("Non-blocking Button Latch:", 
         "The button is debounced in loop() on every iteration,\n"
         "ensuring momentary presses are latched and never missed\n"
         "during the 2-second DHT safe reading delay."),
        ("Internal Pull-Up:", 
         "pinMode(13, INPUT_PULLUP) uses the internal ATmega\n"
         "pullup resistor. Wiring directly from D13 to adjacent GND\n"
         "means zero external resistors are required for the button."),
        ("Atomic Telemetry Payload:", 
         "Serial.print transmits a single compact JSON object every 2s:\n"
         "{\"temp\":28.5,\"humidity\":44,\"light\":185,\"motion\":1,\"button\":1}")
    ]
    ny = 475
    for htitle, hdesc in notes:
        d.text((rx0 + 25, ny), htitle, font=f_body_b, fill=(15, 23, 42))
        ny += 25
        for line in hdesc.split("\n"):
            d.text((rx0 + 25, ny), line, font=f_small, fill=(71, 85, 105))
            ny += 20
        ny += 10

    # Safety & Best Practices Box
    draw_box(d, [rx0, 740, rx0 + rw, 960], fill=(240, 253, 250), outline=(94, 234, 212), radius=12)
    d.text((rx0 + 25, 760), "HARDWARE TIPS & BEST PRACTICES", font=f_header, fill=(15, 118, 110))
    d.text((rx0 + 25, 795), "• DHT11 rate limit: Never poll the DHT11 faster than once every 2s.", font=f_small, fill=(15, 23, 42))
    d.text((rx0 + 25, 825), "• PIR sensor trigger mode: Set the PIR jumper to 'H' (re-triggerable)", font=f_small, fill=(15, 23, 42))
    d.text((rx0 + 25, 850), "  so it holds output HIGH while continuous motion occurs in the room.", font=f_small, fill=(71, 85, 105))
    d.text((rx0 + 25, 880), "• LDR placement: Keep the LDR pointed toward room ambient light", font=f_small, fill=(15, 23, 42))
    d.text((rx0 + 25, 905), "  rather than directly under a harsh desk lamp to avoid saturation.", font=f_small, fill=(71, 85, 105))
    d.text((rx0 + 25, 930), "• USB communication: Baud 9600 matches Pi /dev/ttyACM0 listener.", font=f_small, fill=(15, 23, 42))

    out_path = os.path.join(DOCS, "arduino-schematic.png")
    img.save(out_path)
    print("Saved", out_path)

if __name__ == "__main__":
    generate_system_architecture()
    generate_arduino_schematic()
