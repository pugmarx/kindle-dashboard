import time
import json
import serial
from influxdb import InfluxDBClient
import paho.mqtt.client as mqtt

# Serial config
SERIAL_PORT = "/dev/ttyACM0"
BAUD = 9600

# InfluxDB config
INFLUX_HOST = "localhost"
INFLUX_PORT = 8086
INFLUX_DB = "sensors"
LOCATION = "the_den"

# MQTT config
MQTT_HOST = "localhost"
MQTT_PORT = 1883

try:
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
except Exception:
    mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, *args):
    print("Connected to MQTT broker", flush=True)

def on_disconnect(client, userdata, *args):
    print("MQTT disconnected, will auto-reconnect", flush=True)

mqtt_client.on_connect = on_connect
mqtt_client.on_disconnect = on_disconnect

try:
    mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
    # loop_start() is CRITICAL: runs background network thread to send pings
    # and prevent Mosquitto from dropping the socket after 60 seconds of idle
    mqtt_client.loop_start()
except Exception as e:
    print("MQTT connection error:", e, flush=True)

# InfluxDB client
client = InfluxDBClient(
    host=INFLUX_HOST,
    port=INFLUX_PORT,
    database=INFLUX_DB
)

def connect_serial():
    while True:
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD, timeout=1)
            print("Connected to Arduino on", SERIAL_PORT, flush=True)
            return ser
        except Exception as e:
            time.sleep(2)

ser = connect_serial()

while True:
    try:
        line = ser.readline().decode("utf-8", errors="ignore").strip()
    except Exception as e:
        print("Serial read error, reconnecting:", e, flush=True)
        try:
            ser.close()
        except Exception:
            pass
        ser = connect_serial()
        continue

    if not line:
        continue

    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        continue

    # Instant transient action: fire to MQTT immediately
    if data.get("button") == 1:
        res = mqtt_client.publish("environment/button", "press")
        print(">>> Button pressed! Published to MQTT (rc={})".format(res.rc), flush=True)

    # Time-series metrics: persist to InfluxDB
    point = {
        "measurement": "environment_tagged",
        "tags": {
            "location": LOCATION
        },
        "fields": {
            "temp": float(data["temp"]),
            "humidity": float(data["humidity"]),
            "light": int(data["light"]),
            "motion": int(data["motion"])
        }
    }

    try:
        client.write_points([point])
    except Exception:
        pass
