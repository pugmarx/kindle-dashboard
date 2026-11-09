#!/usr/bin/env python3
# Env Monitor dashboard for a Kindle Paperwhite 2 (landscape).
# Runs on the Raspberry Pi and writes /opt/kindle-feed/dashboard.png every 30 s.
import calendar, json, math, os, re, sys, threading, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

W, H = 1024, 758
DIR = "/opt/kindle-feed/"
SRC = DIR + "status.json"
OUT = DIR + "dashboard.png"
CACHE = DIR + "cache.json"
CONFIG_FILE = DIR + "config.json"

# Default settings (can be overridden in /opt/kindle-feed/config.json)
LAT, LON, PLACE = 51.5074, -0.1278, "London"
ROTATE = 90          # change to 270 if the dashboard appears upside down
NIGHT_FROM, NIGHT_TO = 21, 7   # show inverted (white on black) between these hours
SHIFT = 3                      # pixels to nudge the layout each hour
LIGHT_DIM, LIGHT_BRIGHT = 200, 650   # light sensor: below DIM = Dark, above BRIGHT = Bright

try:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as _cf:
            _cfg = json.load(_cf)
            LAT = _cfg.get("lat", LAT)
            LON = _cfg.get("lon", LON)
            PLACE = _cfg.get("place", PLACE)
            ROTATE = _cfg.get("rotate", ROTATE)
            if "night_from" in _cfg and "night_to" in _cfg:
                NIGHT_FROM, NIGHT_TO = _cfg["night_from"], _cfg["night_to"]
            LIGHT_DIM = _cfg.get("light_dim", LIGHT_DIM)
            LIGHT_BRIGHT = _cfg.get("light_bright", LIGHT_BRIGHT)
except Exception:
    pass

# Fonts: uses a rounded font (Nunito) if its files are in /opt/kindle-feed/fonts/,
# otherwise falls back to the built-in DejaVu Sans.
FONT_DIR = DIR + "fonts/"
ROUND = {True: "Nunito-Bold.ttf", False: "Nunito-Regular.ttf"}
FD = "/usr/share/fonts/truetype/dejavu/"
DEJAVU = {True: "DejaVuSans-Bold.ttf", False: "DejaVuSans.ttf"}

def font(bold, size):
    try:
        return ImageFont.truetype(FONT_DIR + ROUND[bold], size)
    except Exception:
        # DejaVu runs larger than Nunito, so shrink it a little
        return ImageFont.truetype(FD + DEJAVU[bold], int(size * 0.92))

F_CLK = font(True, 120)
F_VAL = font(True, 60)
F_DATE = font(False, 36)
F_REM = font(True, 38)
F_BIG = font(True, 68)
F_LBL = font(False, 30)
F_TXT = font(False, 32)
F_SML = font(False, 23)
F_DET = font(False, 27)
F_WORD = font(True, 38)
F_SEN = font(True, 50)
F_CALT = font(True, 28)

# ---------- helpers ----------
def text_size(d, s, f):
    if hasattr(d, "textbbox"):
        b = d.textbbox((0, 0), s, font=f)
        return b[2] - b[0], b[3] - b[1]
    return d.textsize(s, font=f)

def text_center(d, cx, y, s, f, fill=0):
    w, h = text_size(d, s, f)
    d.text((cx - w // 2, y), s, font=f, fill=fill)

def text_right(d, x, y, s, f, fill=0):
    w, h = text_size(d, s, f)
    d.text((x - w, y), s, font=f, fill=fill)

def wrap(d, text, f, width):
    lines, cur = [], ""
    for word in text.split():
        t = (cur + " " + word).strip()
        if text_size(d, t, f)[0] <= width:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines

def fit(d, text, f, width):
    if text_size(d, text, f)[0] <= width:
        return text
    while text and text_size(d, text + "…", f)[0] > width:
        text = text[:-1]
    return text.rstrip() + "…"

def strip_html(text):
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = clean.replace("&amp;", "&").replace("&quot;", '"').replace("&#039;", "'").replace("&apos;", "'")
    clean = clean.replace("&lt;", "<").replace("&gt;", ">").replace("&#8217;", "'").replace("&#8220;", '"').replace("&#8221;", '"')
    return " ".join(clean.split())

def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "env-monitor/1.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())

def load(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default

def save(path, obj):
    with open(path + ".tmp", "w") as f:
        json.dump(obj, f)
    os.replace(path + ".tmp", path)

def read_status():
    try:
        with open(SRC) as f:
            return json.load(f), os.path.getmtime(SRC)
    except Exception:
        return None, None

# ---------- icons ----------
def thermometer(d, cx, cy):
    d.ellipse([cx-16, cy-62, cx+16, cy-30], fill=0)
    d.rectangle([cx-16, cy-46, cx+16, cy+20], fill=0)
    d.ellipse([cx-10, cy-56, cx+10, cy-36], fill=255)
    d.rectangle([cx-10, cy-46, cx+10, cy+20], fill=255)
    d.rectangle([cx-4, cy-30, cx+4, cy+20], fill=0)
    d.ellipse([cx-28, cy+8, cx+28, cy+64], fill=0)

def droplet(d, cx, cy):
    d.polygon([(cx, cy-60), (cx-36, cy+5), (cx+36, cy+5)], fill=0)
    d.ellipse([cx-38, cy-20, cx+38, cy+56], fill=0)

def sun(d, cx, cy):
    d.ellipse([cx-24, cy-24, cx+24, cy+24], fill=0)
    for i in range(8):
        a = i * math.pi / 4
        d.line([cx + 36*math.cos(a), cy + 36*math.sin(a),
                cx + 56*math.cos(a), cy + 56*math.sin(a)], fill=0, width=8)

def person(d, cx, cy, present):
    d.ellipse([cx-22, cy-60, cx+22, cy-16], fill=0)
    d.pieslice([cx-42, cy-6, cx+42, cy+78], 180, 360, fill=0)
    if not present:
        d.ellipse([cx-15, cy-53, cx+15, cy-23], fill=255)
        d.pieslice([cx-35, cy+1, cx+35, cy+71], 180, 360, fill=255)
        d.rectangle([cx-42, cy+30, cx+42, cy+36], fill=0)

def glass(d, cx, cy):
    d.polygon([(cx-45, cy-60), (cx+45, cy-60), (cx+32, cy+60), (cx-32, cy+60)], fill=0)
    d.polygon([(cx-38, cy-53), (cx+38, cy-53), (cx+26, cy+53), (cx-26, cy+53)], fill=255)
    d.polygon([(cx-33, cy-10), (cx+33, cy-10), (cx+26, cy+53), (cx-26, cy+53)], fill=120)

def _limb(d, pts, w):
    # thick line with rounded ends and joints, pictogram style
    d.line(pts, fill=0, width=w)
    r = w / 2
    for x, y in pts:
        d.ellipse([x - r, y - r, x + r, y + r], fill=0)

def stretcher(d, cx, cy):
    # yoga tree pose: hands joined overhead, one foot resting on the other leg
    d.ellipse([cx-13, cy-58, cx+13, cy-32], fill=0)                      # head
    _limb(d, [(cx, cy-20), (cx, cy+12)], 24)                             # torso
    _limb(d, [(cx-7, cy-22), (cx-28, cy-50), (cx-3, cy-82)], 11)         # left arm
    _limb(d, [(cx+7, cy-22), (cx+28, cy-50), (cx+3, cy-82)], 11)         # right arm
    _limb(d, [(cx-4, cy+16), (cx-4, cy+80)], 14)                         # standing leg
    _limb(d, [(cx+5, cy+18), (cx+36, cy+38), (cx+5, cy+54)], 13)         # bent leg

# ---------- icon rendering ----------
# Icons are drawn 4x larger as a mask, styled, then scaled down smoothly.
class _Scaled:
    def __init__(self, d, s, invert=True):
        self.d, self.s, self.invert = d, s, invert
    def _xy(self, xy):
        out = []
        for v in xy:
            if isinstance(v, (tuple, list)):
                out.append(tuple(c * self.s for c in v))
            else:
                out.append(v * self.s)
        return out
    def _kw(self, kw):
        kw = dict(kw)
        for k in ("fill", "outline"):
            if self.invert and kw.get(k) is not None:
                kw[k] = 255 - kw[k]
        if "width" in kw:
            kw["width"] = int(kw["width"] * self.s)
        return kw
    def ellipse(self, xy, **kw):
        self.d.ellipse(self._xy(xy), **self._kw(kw))
    def rectangle(self, xy, **kw):
        self.d.rectangle(self._xy(xy), **self._kw(kw))
    def polygon(self, xy, **kw):
        self.d.polygon(self._xy(xy), **self._kw(kw))
    def line(self, xy, **kw):
        self.d.line(self._xy(xy), **self._kw(kw))
    def pieslice(self, xy, start, end, **kw):
        self.d.pieslice(self._xy(xy), start, end, **self._kw(kw))
    def arc(self, xy, start, end, **kw):
        self.d.arc(self._xy(xy), start, end, **self._kw(kw))

# clipart-style reflections: small white curved glints on each icon
def gloss_thermometer(d, cx, cy):
    d.arc([cx-19, cy+17, cx+19, cy+55], 165, 245, fill=255, width=5)
    d.ellipse([cx-12, cy+20, cx-6, cy+26], fill=255)

def gloss_droplet(d, cx, cy):
    d.arc([cx-28, cy-10, cx+28, cy+46], 150, 225, fill=255, width=6)
    d.ellipse([cx-9, cy-30, cx-3, cy-22], fill=255)

def gloss_sun(d, cx, cy):
    d.arc([cx-16, cy-16, cx+16, cy+16], 175, 255, fill=255, width=5)

def gloss_person(d, cx, cy):
    d.arc([cx-15, cy-53, cx+15, cy-23], 175, 255, fill=255, width=4)
    d.arc([cx-34, cy+2, cx+34, cy+70], 200, 245, fill=255, width=5)

def gloss_stretcher(d, cx, cy):
    d.arc([cx-9, cy-54, cx+9, cy-36], 175, 255, fill=255, width=3)

def gloss_glass(d, cx, cy):
    d.line([cx-24, cy-2, cx-20, cy+42], fill=255, width=5)

def _cloud(d, cx, cy, fill=0, grow=0):
    g = grow
    d.ellipse([cx-46-g, cy-6-g, cx-6+g, cy+30+g], fill=fill)
    d.ellipse([cx-26-g, cy-30-g, cx+20+g, cy+16+g], fill=fill)
    d.ellipse([cx-2-g, cy-14-g, cx+44+g, cy+30+g], fill=fill)
    d.rectangle([cx-26, cy+4-g, cx+24, cy+30+g], fill=fill)

def w_clear(d, cx, cy):
    d.ellipse([cx-22, cy-22, cx+22, cy+22], fill=0)
    for i in range(8):
        a = i * math.pi / 4
        d.line([cx + 31*math.cos(a), cy + 31*math.sin(a),
                cx + 46*math.cos(a), cy + 46*math.sin(a)], fill=0, width=7)

def w_partly(d, cx, cy):
    sx, sy = cx + 12, cy - 14
    d.ellipse([sx-18, sy-18, sx+18, sy+18], fill=0)
    for i in range(8):
        a = i * math.pi / 4
        d.line([sx + 25*math.cos(a), sy + 25*math.sin(a),
                sx + 36*math.cos(a), sy + 36*math.sin(a)], fill=0, width=6)
    _cloud(d, cx - 2, cy + 14, fill=255, grow=7)
    _cloud(d, cx - 2, cy + 14)

def w_cloud(d, cx, cy):
    _cloud(d, cx, cy + 4)

def w_rain(d, cx, cy):
    _cloud(d, cx, cy - 12)
    for x in (cx - 24, cx, cx + 24):
        d.line([x, cy + 28, x - 7, cy + 46], fill=0, width=6)

def w_storm(d, cx, cy):
    _cloud(d, cx, cy - 12)
    d.polygon([(cx + 4, cy + 18), (cx - 14, cy + 40), (cx - 2, cy + 40),
               (cx - 10, cy + 56), (cx + 14, cy + 32), (cx + 2, cy + 32),
               (cx + 10, cy + 18)], fill=0)

def newspaper(d, cx, cy):
    d.rectangle([cx-22, cy-18, cx+22, cy+18], fill=0)
    d.rectangle([cx-18, cy-14, cx+18, cy+14], fill=255)
    d.rectangle([cx-14, cy-10, cx-1, cy+2], fill=0)
    for y in (cy-10, cy-4, cy+2):
        d.line([cx+3, y, cx+14, y], fill=0, width=3)
    for y in (cy+7, cy+11):
        d.line([cx-14, y, cx+14, y], fill=0, width=2)

def gloss_cloud(d, cx, cy):
    d.arc([cx-22, cy-26, cx+16, cy+12], 190, 260, fill=255, width=5)

def gloss_w_clear(d, cx, cy):
    d.arc([cx-15, cy-15, cx+15, cy+15], 175, 255, fill=255, width=5)

def gloss_w_partly(d, cx, cy):
    gloss_cloud(d, cx - 2, cy + 14)

def gloss_w_cloud(d, cx, cy):
    gloss_cloud(d, cx, cy + 4)

def gloss_w_rain(d, cx, cy):
    gloss_cloud(d, cx, cy - 12)

def weather_icon(code):
    if code is None:
        return None
    if code == 0:
        return w_clear, "w_clear"
    if code < 3:
        return w_partly, "w_partly"
    if code < 50:
        return w_cloud, "w_cloud"
    if code < 95:
        return w_rain, "w_rain"
    return w_storm, "w_storm"

GLOSS = {"thermometer": gloss_thermometer, "droplet": gloss_droplet,
         "sun": gloss_sun, "person1": gloss_person, "glass": gloss_glass,
         "stretcher": gloss_stretcher,
         "w_clear": gloss_w_clear, "w_partly": gloss_w_partly,
         "w_cloud": gloss_w_cloud, "w_rain": gloss_w_rain, "w_storm": gloss_w_rain}

_ICONS = {}
ICON_BOX = 180

def is_night():
    h = time.localtime().tm_hour
    return h >= NIGHT_FROM or h < NIGHT_TO

def shaded(fn, key, night=False, box=ICON_BOX, scale=1.0):
    # Day: flat black icon with small white reflections.
    # Night: white icon with a soft glow.
    ck = (key, night, box, scale)
    if ck in _ICONS:
        return _ICONS[ck]
    S = 4
    N = box * S
    c = box // 2
    mask = Image.new("L", (N, N), 0)
    fn(_Scaled(ImageDraw.Draw(mask), S * scale), c / scale, c / scale)

    if night:
        glow = mask.filter(ImageFilter.GaussianBlur(9 * S * scale)).point(lambda v: int(v * 0.7))
        # fade the glow out before the edge of the box so no square shows
        edge = Image.new("L", (N, N), 0)
        ImageDraw.Draw(edge).rectangle([8 * S, 8 * S, N - 8 * S, N - 8 * S], fill=255)
        glow = ImageChops.multiply(glow, edge.filter(ImageFilter.GaussianBlur(5 * S)))
        out = Image.new("L", (N, N), 0)
        out.paste(Image.new("L", (N, N), 130), (0, 0), glow)
        out.paste(Image.new("L", (N, N), 255), (0, 0), mask)
        out = ImageOps.invert(out)       # the whole page is inverted at night
    else:
        out = Image.new("L", (N, N), 255)
        out.paste(Image.new("L", (N, N), 0), (0, 0), mask)
        if key in GLOSS:
            gl = Image.new("L", (N, N), 0)
            GLOSS[key](_Scaled(ImageDraw.Draw(gl), S * scale, invert=False),
                       c / scale, c / scale)
            gl = ImageChops.multiply(gl, mask).filter(ImageFilter.GaussianBlur(S // 2))
            out.paste(Image.new("L", (N, N), 245), (0, 0), gl)
    _ICONS[ck] = out.resize((box, box), Image.LANCZOS)
    return _ICONS[ck]

def draw_icon(img, fn, cx, cy, key, box=ICON_BOX, scale=1.0):
    # blend with "darker" so the icon's white background never covers
    # nearby text or lines
    x, y = cx - box // 2, cy - box // 2
    region = img.crop((x, y, x + box, y + box))
    img.paste(ImageChops.darker(region, shaded(fn, key, is_night(), box, scale)), (x, y))

# ---------- data ----------
def describe(code):
    if code is None:
        return ""
    if code == 0:
        return "Clear"
    if code < 3:
        return "Partly cloudy"
    if code == 3:
        return "Cloudy"
    if code in (45, 48):
        return "Foggy"
    if code < 60:
        return "Drizzle"
    if code < 70:
        return "Rain"
    if code < 80:
        return "Snow"
    if code < 90:
        return "Showers"
    return "Storms"

def mood(data, aqi=None):
    if not data:
        return ""
    try:
        t = float(data.get("temp"))
    except Exception:
        return ""
    if t >= 30:
        m = "Hot in here"
    elif t >= 27:
        m = "Warm"
    elif t <= 18:
        m = "Chilly"
    else:
        m = "Comfortable"
    try:
        h = float(data.get("hum"))
        if h < 30:
            m += " and dry"
        elif h > 70:
            m += " and humid"
    except Exception:
        pass
    poor_air = aqi is not None and aqi > 150
    if t >= 30 and poor_air:
        m += ", but the air outside is poor, so keep windows shut"
    elif t >= 30:
        m += ", maybe open a window"
    elif poor_air:
        m += ". Air outside is poor, keep windows shut"
    return m + "."

def reminder():
    t = time.localtime()
    if not 9 <= t.tm_hour < 21:
        return None
    if t.tm_min < 5:
        return "water"
    if t.tm_hour % 2 == 0 and 30 <= t.tm_min < 35:
        return "stretch"
    return None

def update_net(cache):
    now = time.time()

    # outdoor weather: every 15 minutes
    if now - cache.get("weather_t", 0) > 900 or "sunrise" not in cache.get("weather", {}):
        try:
            u = ("https://api.open-meteo.com/v1/forecast?latitude={}&longitude={}"
                 "&current=temperature_2m,relative_humidity_2m,weather_code,"
                 "apparent_temperature"
                 "&daily=temperature_2m_max,temperature_2m_min,sunrise,sunset,"
                 "precipitation_probability_max"
                 "&forecast_days=1&timezone=auto").format(LAT, LON)
            j = get_json(u)
            c, dl = j["current"], j.get("daily", {})
            def first(k):
                v = dl.get(k) or [None]
                return v[0]
            cache["weather"] = {"temp": c["temperature_2m"],
                                "hum": c["relative_humidity_2m"],
                                "code": c["weather_code"],
                                "feels": c.get("apparent_temperature"),
                                "hi": first("temperature_2m_max"),
                                "lo": first("temperature_2m_min"),
                                "rain": first("precipitation_probability_max"),
                                "sunrise": (first("sunrise") or "")[11:16],
                                "sunset": (first("sunset") or "")[11:16]}
        except Exception:
            pass
        cache["weather_t"] = now

    # NASA headlines: every hour
    if now - cache.get("nasa_t", 0) > 3600:
        try:
            req = urllib.request.Request("https://www.nasa.gov/news-release/feed/",
                                         headers={"User-Agent": "env-monitor/1.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                root = ET.fromstring(r.read())
            titles = [(i.findtext("title") or "").strip() for i in root.iter("item")]
            titles = [t for t in titles if t][:10]
            if titles:
                cache["nasa"] = titles
        except Exception:
            pass
        cache["nasa_t"] = now

    # outdoor air quality: every 30 minutes
    if now - cache.get("air_t", 0) > 1800:
        try:
            u = ("https://air-quality-api.open-meteo.com/v1/air-quality?latitude={}"
                 "&longitude={}&current=us_aqi,pm2_5&timezone=auto").format(LAT, LON)
            c = get_json(u)["current"]
            cache["air"] = {"aqi": c.get("us_aqi"), "pm25": c.get("pm2_5")}
        except Exception:
            pass
        cache["air_t"] = now

    # tech headlines: every hour (or immediately if cached items lack direct article URLs)
    needs_news = (now - cache.get("news_t", 0) > 3600 or
                  not cache.get("tech") or
                  not any("url" in item for item in cache["tech"]))
    if needs_news:
        try:
            ids = get_json("https://hacker-news.firebaseio.com/v0/topstories.json")[:12]
            items = []
            for i in ids:
                item = get_json("https://hacker-news.firebaseio.com/v0/item/{}.json".format(i))
                if item and item.get("title"):
                    site = urllib.parse.urlparse(item.get("url") or "").netloc
                    if site.startswith("www."):
                        site = site[4:]
                    story_url = item.get("url")
                    hn_url = "https://news.ycombinator.com/item?id={}".format(item["id"])
                    items.append({"title": item["title"],
                                  "site": site or "news.ycombinator.com",
                                  "points": item.get("score", 0),
                                  "comments": item.get("descendants", 0),
                                  "url": story_url or hn_url,
                                  "hn_url": hn_url,
                                  "id": item["id"]})
            if items:
                cache["tech"] = items
        except Exception:
            pass
        cache["news_t"] = now

    # AI news with rich context: every 2 hours (or immediately if cached items lack summaries)
    needs_ai = (now - cache.get("ai_t", 0) > 7200 or
                not cache.get("ai_news") or
                not any(item.get("summary") for item in cache.get("ai_news", [])))
    if needs_ai:
        ai_items = []
        # Source 1: Ars Technica AI (high quality reporting with summary paragraphs)
        try:
            req = urllib.request.Request("https://arstechnica.com/ai/feed/",
                                         headers={"User-Agent": "Mozilla/5.0 (compatible; EnvMonitor/1.0)"})
            with urllib.request.urlopen(req, timeout=15) as r:
                root = ET.fromstring(r.read())
            for item in root.iter("item"):
                t = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                desc = item.findtext("description") or item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded") or ""
                desc = strip_html(desc)
                if t and link:
                    ai_items.append({
                        "title": t,
                        "url": link,
                        "summary": desc[:350],
                        "source": "Ars Technica"
                    })
        except Exception:
            pass

        # Source 2: VentureBeat AI (frontier releases and enterprise updates)
        if len(ai_items) < 6:
            try:
                req = urllib.request.Request("https://venturebeat.com/category/ai/feed/",
                                             headers={"User-Agent": "Mozilla/5.0 (compatible; EnvMonitor/1.0)"})
                with urllib.request.urlopen(req, timeout=15) as r:
                    root = ET.fromstring(r.read())
                for item in root.iter("item"):
                    t = (item.findtext("title") or "").strip()
                    link = (item.findtext("link") or "").strip()
                    desc = item.findtext("description") or item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded") or ""
                    desc = strip_html(desc)
                    if t and link:
                        ai_items.append({
                            "title": t,
                            "url": link,
                            "summary": desc[:350],
                            "source": "VentureBeat"
                        })
            except Exception:
                pass

        if ai_items:
            cache["ai_news"] = ai_items[:6]
            print(">>> Fetched {} AI news items with context".format(len(ai_items)), flush=True)
        cache["ai_t"] = now

# ---------- right-side blocks ----------
RX0, RX1 = 540, 1004            # right column edges
RCX = (RX0 + RX1) // 2          # right column centre

def block_news(img, d, news, now):
    draw_icon(img, planet, RX0 + 26, 38, "planet", box=70, scale=0.62)
    d.text((RX0 + 62, 26), "NASA", font=F_SML, fill=60)
    if not news:
        d.text((RX0, 62), "Fetching NASA news…", font=F_TXT, fill=60)
        return
    headline = news[int(now // 60) % len(news)]
    lines = wrap(d, headline, F_TXT, RX1 - RX0)
    if len(lines) > 3:
        lines = lines[:2] + [fit(d, " ".join(lines[2:]), F_TXT, RX1 - RX0)]
    y = 62
    for line in lines:
        d.text((RX0, y), line, font=F_TXT, fill=0)
        y += 40

def block_reminder(img, d, kind):
    if kind == "water":
        draw_icon(img, glass, 610, 112, "glass")
        title, sub = "Drink some water", "A glass now keeps you sharp."
    else:
        draw_icon(img, stretcher, 610, 116, "stretcher")
        title, sub = "Time to stretch", "Stand tall, reach up and take a few deep breaths."
    y = 40
    for line in wrap(d, title, F_REM, RX1 - 700):
        d.text((700, y), line, font=F_REM, fill=0)
        y += 44
    y += 8
    for line in wrap(d, sub, F_SML, RX1 - 700)[:3]:
        d.text((700, y), line, font=F_SML, fill=30)
        y += 30

def block_clock(d):
    text_center(d, RCX, 216, time.strftime("%H:%M"), F_CLK)
    text_center(d, RCX, 350, time.strftime("%a, %Y.%m.%d"), F_DATE, fill=30)

def moon_phase():
    # fraction of the lunar cycle: 0 = new, 0.25 = first quarter,
    # 0.5 = full, 0.75 = last quarter
    days = time.time() / 86400 + 2440587.5 - 2451550.1
    f = (days % 29.530588853) / 29.530588853
    names = ["New moon", "Waxing crescent", "First quarter", "Waxing gibbous",
             "Full moon", "Waning gibbous", "Last quarter", "Waning crescent"]
    name = names[int((f * 8) + 0.5) % 8]
    lit = (1 - math.cos(2 * math.pi * f)) / 2
    return f, name, lit

def moon_image(f, box, night):
    S = 4
    N = box * S
    r = N // 2 - 3 * S
    c = N // 2
    k = math.cos(2 * math.pi * f)
    dark, lit_v, ring, bg = (70, 255, 160, 0) if night else (40, 255, 0, 255)
    im = Image.new("L", (N, N), bg)
    px = im.load()
    for y in range(N):
        ny = (y - c) / r
        if abs(ny) > 1:
            continue
        span = math.sqrt(1 - ny * ny)
        for x in range(N):
            nx = (x - c) / r
            if abs(nx) > span:
                continue
            if f < 0.5:
                is_lit = nx > k * span
            else:
                is_lit = nx < -k * span
            px[x, y] = lit_v if is_lit else dark
    ImageDraw.Draw(im).ellipse([c - r, c - r, c + r, c + r], outline=ring, width=S * 3)
    im = im.resize((box, box), Image.LANCZOS)
    return ImageOps.invert(im) if night else im   # page is inverted at night

_MOON = {}
def draw_moon(img, cx, cy, box):
    f, name, lit = moon_phase()
    key = (round(f, 2), box, is_night())
    if key not in _MOON:
        _MOON.clear()
        _MOON[key] = moon_image(f, box, is_night())
    x, y = cx - box // 2, cy - box // 2
    region = img.crop((x, y, x + box, y + box))
    img.paste(ImageChops.darker(region, _MOON[key]), (x, y))
    return name, lit

def deg(v):
    return "–" if v is None else "{}°".format(round(v))

def block_weather(img, d, w, air=None):
    d.text((RX0, 450), "OUTSIDE · " + PLACE.upper(), font=F_SML, fill=60)
    if not w:
        d.text((RX0, 520), "No weather yet", font=F_LBL, fill=0)
    else:
        # top row: icon + temperature + conditions | details column
        icon = weather_icon(w.get("code"))
        if icon:
            draw_icon(img, icon[0], RX0 + 52, 534, icon[1], box=104)
        d.text((RX0 + 118, 480), deg(w.get("temp")), font=F_BIG, fill=0)
        d.text((RX0 + 121, 560), fit(d, describe(w.get("code")), F_DET, 172),
               font=F_DET, fill=0)
        rows = ["Feels " + deg(w.get("feels")),
                "H {}  L {}".format(deg(w.get("hi")), deg(w.get("lo")))]
        if w.get("rain") is not None:
            rows.append("Rain {}%".format(w.get("rain")))
        rows.append("Hum. {}%".format(w.get("hum")))
        if air and air.get("aqi") is not None:
            a = round(air["aqi"])
            rows.append("AQI {} {}".format(a, aqi_word(a)))
        y = 470
        for row in rows:
            d.text((846, y), fit(d, row, F_DET, 158), font=F_DET, fill=0)
            y += 29

    d.line([RX0, 622, RX1, 622], fill=190, width=2)

    # bottom row: sunrise & sunset on the left, moon phase on the right
    if w and w.get("sunrise"):
        d.text((RX0, 634), "Sunrise  " + w["sunrise"], font=F_DET, fill=0)
        d.text((RX0, 664), "Sunset   " + w["sunset"], font=F_DET, fill=0)
    name, lit = draw_moon(img, 778, 668, 54)
    nf = F_DET if text_size(d, name, F_DET)[0] <= 190 else F_SML
    d.text((812, 634 if nf is F_DET else 638), name, font=nf, fill=0)
    d.text((812, 664), "{}% lit".format(round(lit * 100)), font=F_DET, fill=40)

def light_word(v):
    try:
        v = float(v)
    except Exception:
        return "-"
    if v < LIGHT_DIM:
        return "Dark"
    if v < LIGHT_BRIGHT:
        return "Dim"
    return "Bright"

def aqi_word(a):
    if a < 51:
        return "Good"
    if a < 101:
        return "Fair"
    if a < 151:
        return "Poor"
    if a < 201:
        return "Bad"
    return "Severe"

def update_today(cache, data):
    # today's lowest/highest room temperature and humidity
    day = time.strftime("%Y-%m-%d")
    t = cache.get("today")
    if not t or t.get("day") != day:
        t = {"day": day}
    for k in ("temp", "hum"):
        try:
            v = float(data[k])
        except Exception:
            continue
        t[k + "_lo"] = min(v, t.get(k + "_lo", v))
        t[k + "_hi"] = max(v, t.get(k + "_hi", v))
    cache["today"] = t
    return t

def rng(lo, hi, unit):
    if lo is None:
        return ""
    if round(lo) == round(hi):
        return "today {:.0f}{}".format(lo, unit)
    return "today {:.0f}–{:.0f}{}".format(lo, hi, unit)

def block_sensors(img, d, data, today):
    d.line([20, 196, 492, 196], fill=180, width=2)
    d.line([256, 24, 256, 372], fill=180, width=2)
    if not data:
        text_center(d, 256, 150, "No sensor data", F_TXT)
        return
    motion = str(data.get("motion")) == "1"
    def num(v):
        try:
            return "{:.0f}".format(float(v))
        except Exception:
            return "-"
    t, h = num(data.get("temp")), num(data.get("hum"))
    cells = [
        (thermometer, "thermometer", "{}°C".format(t), F_SEN,
         rng(today.get("temp_lo"), today.get("temp_hi"), "°")),
        (droplet, "droplet", "{}%".format(h), F_SEN,
         rng(today.get("hum_lo"), today.get("hum_hi"), "%")),
        (sun, "sun", light_word(data.get("light")), F_WORD,
         "level {}".format(data.get("light", "-"))),
        (lambda d, x, y: person(d, x, y, motion), "person%d" % motion,
         "Here" if motion else "Empty", F_WORD, ""),
    ]
    for i, (icon, key, value, vf, sub) in enumerate(cells):
        x0 = (i % 2) * 256
        cy = 100 + (i // 2) * 190
        draw_icon(img, icon, x0 + 50, cy, key, box=116, scale=0.72)
        vy = cy - 38 if vf is F_SEN else cy - 30
        d.text((x0 + 98, vy), fit(d, value, vf, 152), font=vf, fill=0)
        if sub:
            if text_size(d, sub, F_SML)[0] > 152:
                sub = sub.replace("today ", "")
            d.text((x0 + 100, cy + 26), fit(d, sub, F_SML, 152), font=F_SML, fill=50)

def planet(d, cx, cy):
    d.ellipse([cx-40, cy-12, cx+40, cy+12], outline=0, width=5)          # ring (back)
    d.ellipse([cx-21, cy-21, cx+21, cy+21], fill=0)                      # planet
    d.arc([cx-40, cy-12, cx+40, cy+12], 0, 180, fill=255, width=11)      # gap
    d.arc([cx-40, cy-12, cx+40, cy+12], 0, 180, fill=0, width=5)         # ring (front)

def gloss_planet(d, cx, cy):
    d.arc([cx-14, cy-14, cx+14, cy+14], 185, 255, fill=255, width=4)

GLOSS["planet"] = gloss_planet

PANEL_TOP = 384     # bottom-left panel: calendar and tech news take turns

def block_calendar(d):
    t = time.localtime()
    d.text((24, PANEL_TOP + 12), time.strftime("%B %Y"), font=F_CALT, fill=0)
    cols = [20 + 472 * (i + 0.5) / 7 for i in range(7)]
    for i, name in enumerate(["M", "T", "W", "T", "F", "S", "S"]):
        text_center(d, int(cols[i]), PANEL_TOP + 58, name, F_SML, fill=0 if i < 5 else 110)
    weeks = calendar.Calendar(0).monthdayscalendar(t.tm_year, t.tm_mon)
    step = 40 if len(weeks) <= 5 else 34
    for r, week in enumerate(weeks):
        y = PANEL_TOP + 92 + r * step
        for c, day in enumerate(week):
            if not day:
                continue
            cx = int(cols[c])
            if day == t.tm_mday:
                d.ellipse([cx - 19, y - 3, cx + 19, y + 33], fill=0)
                text_center(d, cx, y, str(day), F_DET, fill=255)
            else:
                text_center(d, cx, y, str(day), F_DET, fill=0 if c < 5 else 110)

def block_tech(img, d, tech, now):
    draw_icon(img, newspaper, 46, PANEL_TOP + 32, "newspaper", box=60)
    d.text((82, PANEL_TOP + 20), "TECH NEWS", font=F_SML, fill=60)
    per_page = 2
    pages = max(1, (len(tech) + per_page - 1) // per_page)
    start = (int(now // 60) % pages) * per_page
    y = PANEL_TOP + 62
    for k in range(3):                      # two stories, a third if it fits
        item = tech[(start + k) % len(tech)]
        if k == 2 and len(tech) < 3:
            break
        lines = wrap(d, item["title"], F_TXT, 468)
        if len(lines) > 2:
            lines = [lines[0], fit(d, " ".join(lines[1:]), F_TXT, 468)]
        if k == 2 and y + 40 * len(lines) + 32 > 710:
            break
        for line in lines:
            d.text((24, y), line, font=F_TXT, fill=0)
            y += 40
        pts = item.get("points", 0)
        meta = "{} · {} point{}".format(item.get("site", ""), pts, "" if pts == 1 else "s")
        d.text((24, y + 2), fit(d, meta, F_SML, 468), font=F_SML, fill=50)
        y += 50

# ---------- qr code & full-screen reader ----------
def make_qr(url, size=150):
    try:
        import qrcode
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=5,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("L")
        return img.resize((size, size), Image.NEAREST)
    except Exception:
        # Stylized placeholder with finder patterns if qrcode package is missing
        img = Image.new("L", (size, size), 255)
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, size - 1, size - 1], outline=0, width=2)
        for cx, cy in [(24, 24), (size - 25, 24), (24, size - 25)]:
            d.rectangle([cx - 16, cy - 16, cx + 16, cy + 16], fill=0)
            d.rectangle([cx - 10, cy - 10, cx + 10, cy + 10], fill=255)
            d.rectangle([cx - 5, cy - 5, cx + 5, cy + 5], fill=0)
        text_center(d, size // 2, size // 2 - 8, "QR CODE", F_SML, fill=0)
        text_center(d, size // 2, size // 2 + 12, "scan on phone", font(False, 18), fill=90)
        return img

def render_tech_screen(img, d, tech, now):
    # Header
    draw_icon(img, newspaper, 46, 42, "newspaper", box=60, scale=0.7)
    d.text((82, 28), "TECH NEWS", font=font(True, 32), fill=0)
    text_right(d, 994, 32, time.strftime("%H:%M  %a, %b %d"), font(True, 26), fill=0)
    d.line([30, 78, 994, 78], fill=0, width=2)

    if not tech:
        text_center(d, W // 2, H // 2, "Fetching top stories…", F_TXT, fill=80)
        return

    # Top 3 stories with generous spacing
    cards = tech[:3]
    y_starts = [96, 304, 512]

    for idx, item in enumerate(cards):
        y0 = y_starts[idx]
        hn_fallback = "https://news.ycombinator.com/item?id={}".format(item.get("id")) if item.get("id") else "https://news.ycombinator.com"
        url = item.get("url") or item.get("hn_url") or hn_fallback

        # Story text on the left (x = 40 to 810)
        pts = item.get("points", 0)
        site = item.get("site", "news.ycombinator.com")
        meta = "#{}  ·  {}  ·  {} pt{}".format(idx + 1, site, pts, "" if pts == 1 else "s")
        if item.get("comments") is not None:
            meta += "  ·  {} comment{}".format(item["comments"], "" if item["comments"] == 1 else "s")
        d.text((40, y0 + 10), meta, font=font(True, 24), fill=60)

        # Headline
        lines = wrap(d, item["title"], font(True, 32), 760)
        if len(lines) > 2:
            lines = [lines[0], fit(d, " ".join(lines[1:]), font(True, 32), 760)]
        ty = y0 + 46
        for line in lines:
            d.text((40, ty), line, font=font(True, 32), fill=0)
            ty += 40

        # 150x150 QR code on the right (x = 834 to 984)
        qr_img = make_qr(url, size=150)
        img.paste(qr_img, (834, y0 + 8))
        d.rectangle([833, y0 + 7, 985, y0 + 159], outline=180, width=1)

        # Row divider
        if idx < 2:
            d.line([30, y0 + 192, 994, y0 + 192], fill=210, width=1)

    # Footer
    d.line([30, 716, 994, 716], fill=0, width=2)
    text_right(d, 994, 726, "Updated " + time.strftime("%H:%M"), F_SML, fill=80)


def render_ai_screen(img, d, cache, now):
    # Header
    draw_icon(img, planet, 46, 42, "planet", box=60, scale=0.7)
    d.text((82, 28), "AI DIGEST", font=font(True, 32), fill=0)
    text_right(d, 994, 32, time.strftime("%H:%M  %a, %b %d"), font(True, 26), fill=0)
    d.line([30, 78, 994, 78], fill=0, width=2)

    ai_news = cache.get("ai_news", [])
    if not ai_news:
        text_center(d, W // 2, H // 2, "Fetching AI news & context…", F_TXT, fill=80)
        return

    # 3 major AI stories with rich context paragraphs and QR codes on the right
    cards = ai_news[:3]
    y_starts = [96, 304, 512]

    for idx, item in enumerate(cards):
        y0 = y_starts[idx]
        url = item.get("url", "https://arstechnica.com/ai/")

        # Source / rank
        meta = "#{}  ·  {}".format(idx + 1, item.get("source", "AI News"))
        d.text((40, y0 + 8), meta, font=font(True, 24), fill=60)

        # Headline (bold, 1-2 lines)
        title_lines = wrap(d, item["title"], font(True, 28), 760)
        if len(title_lines) > 2:
            title_lines = [title_lines[0], fit(d, " ".join(title_lines[1:]), font(True, 28), 760)]
        ty = y0 + 38
        for line in title_lines:
            d.text((40, ty), line, font=font(True, 28), fill=0)
            ty += 34

        # Context / Summary paragraph (2-3 lines of key takeaways)
        summary = item.get("summary", "")
        if summary:
            summary_lines = wrap(d, summary, font(False, 23), 760)
            max_lines = 4 - len(title_lines)
            if len(summary_lines) > max_lines:
                summary_lines = summary_lines[:max_lines-1] + [fit(d, " ".join(summary_lines[max_lines-1:]), font(False, 23), 760)]
            sy = ty + 6
            for line in summary_lines:
                d.text((40, sy), line, font=font(False, 23), fill=40)
                sy += 28

        # 150x150 QR code on the right (x = 834 to 984)
        qr_img = make_qr(url, size=150)
        img.paste(qr_img, (834, y0 + 8))
        d.rectangle([833, y0 + 7, 985, y0 + 159], outline=180, width=1)

        # Row divider
        if idx < 2:
            d.line([30, y0 + 192, 994, y0 + 192], fill=210, width=1)

    # Footer
    d.line([30, 716, 994, 716], fill=0, width=2)
    text_right(d, 994, 726, "Updated " + time.strftime("%H:%M"), F_SML, fill=80)

# ---------- page ----------
def render(cache):
    now = time.time()
    # Auto-timeout: revert to main dashboard after 5 minutes
    if cache.get("view", "dash") != "dash" and (now - cache.get("view_time", 0)) > 300:
        cache["view"] = "dash"

    view = cache.get("view", "dash")
    if view == "tech":
        img = Image.new("L", (W, H), 255)
        d = ImageDraw.Draw(img)
        render_tech_screen(img, d, cache.get("tech"), now)
        return img
    elif view == "ai":
        img = Image.new("L", (W, H), 255)
        d = ImageDraw.Draw(img)
        render_ai_screen(img, d, cache, now)
        return img

    data, mtime = read_status()
    img = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(img)

    # left half: compact sensor grid on top, month calendar below
    d.line([512, 20, 512, 696], fill=0, width=2)
    today = update_today(cache, data) if data else cache.get("today", {})
    block_sensors(img, d, data, today)
    d.line([20, PANEL_TOP, 492, PANEL_TOP], fill=180, width=2)
    if (int(now) // 180) % 2 == 0 or not cache.get("tech"):
        block_calendar(d)
    else:
        block_tech(img, d, cache.get("tech"), now)

    # right top: reminder when due, otherwise a tech headline
    r = reminder()
    if r:
        block_reminder(img, d, r)
    else:
        block_news(img, d, cache.get("nasa"), now)
    d.line([RX0, 210, RX1, 210], fill=180, width=2)

    # right middle: clock and date
    block_clock(d)
    d.line([RX0, 434, RX1, 434], fill=180, width=2)

    # right bottom: outdoor weather panel with moon phase
    block_weather(img, d, cache.get("weather"), cache.get("air"))

    # footer: room mood + last sensor update
    d.line([0, 716, W, 716], fill=0, width=2)
    d.text((20, 724), fit(d, mood(data, (cache.get("air") or {}).get("aqi")), F_SML, 820), font=F_SML, fill=0)
    if mtime:
        stamp = "Updated " + time.strftime("%H:%M", time.localtime(mtime))
        if now - mtime > 300:
            stamp = "No new data since " + time.strftime("%H:%M", time.localtime(mtime))
        text_right(d, 1004, 724, stamp, F_SML, fill=50)
    return img

def protect(img):
    # screen care: nudge the layout a few pixels every hour, and invert it
    # at night so every pixel regularly changes state
    t = time.localtime()
    offsets = [(0, 0), (1, 0), (1, 1), (0, 1), (-1, 1),
               (-1, 0), (-1, -1), (0, -1), (1, -1)]
    dx, dy = offsets[t.tm_hour % len(offsets)]
    out = Image.new("L", img.size, 255)
    out.paste(img, (dx * SHIFT, dy * SHIFT))
    return ImageOps.invert(out) if is_night() else out

def fetch_loop(cache):
    # internet fetches run in the background, so a slow or hanging
    # service can never hold up the dashboard
    while True:
        try:
            update_net(cache)
        except Exception:
            pass
        time.sleep(60)

TRIGGER_EVENT = threading.Event()

VIEWS = ["dash", "tech", "ai"]

def button_listener(cache):
    def toggle():
        curr = cache.get("view", "dash")
        idx = (VIEWS.index(curr) + 1) % len(VIEWS) if curr in VIEWS else 0
        cache["view"] = VIEWS[idx]
        cache["view_time"] = time.time()
        print(">>> Button pressed! View changed to:", cache["view"], flush=True)
        TRIGGER_EVENT.set()

    # Try paho-mqtt first
    try:
        import paho.mqtt.client as mqtt
        def on_connect(client, userdata, flags, *args):
            client.subscribe("environment/button")
            print(">>> MQTT listener subscribed to environment/button", flush=True)

        def on_message(client, userdata, msg):
            toggle()

        try:
            # Paho-mqtt v2 compatibility
            c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        except Exception:
            c = mqtt.Client()

        c.on_connect = on_connect
        c.on_message = on_message
        c.connect("localhost", 1883, 60)
        c.loop_forever()
        return
    except Exception as e:
        print(">>> paho-mqtt listener error:", e, "- falling back to mosquitto_sub", flush=True)

    # Fallback to mosquitto_sub binary (always available on the Pi)
    try:
        import subprocess
        print(">>> Starting mosquitto_sub fallback listener", flush=True)
        # stdbuf -oL forces line-buffering so single-line MQTT messages aren't buffered
        cmd = ["stdbuf", "-oL", "mosquitto_sub", "-h", "localhost", "-t", "environment/button"]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             universal_newlines=True, bufsize=1)
        while True:
            line = p.stdout.readline()
            if not line:
                break
            toggle()
    except Exception as e:
        print(">>> mosquitto_sub fallback error:", e, flush=True)

def main():
    once = "--once" in sys.argv
    cache = load(CACHE, {})
    cache.pop("history", None)
    if once:
        update_net(cache)
    else:
        threading.Thread(target=fetch_loop, args=(cache,), daemon=True).start()
        threading.Thread(target=button_listener, args=(cache,), daemon=True).start()
    while True:
        save(CACHE, dict(cache))
        img = protect(render(cache)).rotate(ROTATE, expand=True)
        img.save(OUT + ".tmp.png")
        os.replace(OUT + ".tmp.png", OUT)
        if once:
            break
        TRIGGER_EVENT.wait(30)
        TRIGGER_EVENT.clear()

if __name__ == "__main__":
    main()
