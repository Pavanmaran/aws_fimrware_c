"""
ESP32 -> AWS IoT Core -> Python -> Flask dashboard
====================================================

Data flow (read this first!):

    [ESP32 + light sensor]
            |  publishes JSON every 2 sec to topic  factory/machine01/telemetry
            v
    [AWS IoT Core]   (the MQTT "post office")
            |  we SUBSCRIBE to the same topic
            v
    [this file: MQTT client thread]  -> stores readings in a list in memory
            |
            v
    [Flask web server]  -> /api/data gives JSON -> browser page draws the charts

Run it:
    cd dashboard
    pip install -r requirements.txt
    python app.py
Then open  http://localhost:5000  in your browser.
"""

import json
import os
import threading
import time
from collections import deque

from flask import Flask, jsonify, render_template
from awscrt import mqtt5
from awsiot import mqtt5_client_builder

# ---------------------------------------------------------------------------
# 1. SETTINGS  (same values as your ESP32 code)
# ---------------------------------------------------------------------------
ENDPOINT = "a1dkr9puunhret-ats.iot.us-east-1.amazonaws.com"
TOPIC = "factory/machine01/telemetry"   # must match TOPIC in the ESP32 code

# IMPORTANT: every MQTT device needs a UNIQUE client id.
# If we used "machineMonitor" (the ESP32's id), AWS would disconnect the ESP32!
# "basicPubSub" is already allowed in your IoT policy, so we use that.
CLIENT_ID = "basicPubSub"

# Certificates live in the parent folder (connect_device_package).
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CERT_DIR = os.path.dirname(BASE_DIR)
CERT_PATH = os.path.join(CERT_DIR, "machineMonitor.cert.pem")
KEY_PATH = os.path.join(CERT_DIR, "machineMonitor.private.key")
CA_PATH = os.path.join(CERT_DIR, "root-CA.crt")

# How many recent readings to remember (2 sec each -> 100 = ~3 minutes).
MAX_POINTS = 100

# ---------------------------------------------------------------------------
# 2. SHARED DATA
# ---------------------------------------------------------------------------
# deque = a list that automatically drops the oldest item when it is full.
# The MQTT thread WRITES to it, Flask routes READ from it.
readings = deque(maxlen=MAX_POINTS)
status = {"connected": False}   # shown as the green/red dot on the page


# ---------------------------------------------------------------------------
# 3. MQTT PART  (runs in the background, talks to AWS)
# ---------------------------------------------------------------------------
def on_message(data):
    """Called automatically every time AWS delivers a message on our topic."""
    try:
        msg = json.loads(data.publish_packet.payload.decode())
    except (ValueError, UnicodeDecodeError):
        print("Ignoring non-JSON message")
        return
    # Add the time we received it (the ESP32 doesn't send a timestamp).
    msg["ts"] = time.time()
    readings.append(msg)
    print("Received:", msg)


def on_connected(event):
    """Called when the connection to AWS succeeds."""
    status["connected"] = True
    print("Connected to AWS IoT")
    # Subscribe = "tell AWS: send me everything published on this topic".
    # This is done here so it also re-runs after an automatic reconnect.
    future = client.subscribe(mqtt5.SubscribePacket(
        subscriptions=[mqtt5.Subscription(topic_filter=TOPIC,
                                          qos=mqtt5.QoS.AT_LEAST_ONCE)]))
    # Don't wait (future.result()) inside this callback - it runs on the same
    # thread that would deliver the answer, so it would freeze. Use a callback.
    future.add_done_callback(on_subscribed)


def on_subscribed(future):
    """Called when AWS answers our subscribe request."""
    try:
        suback = future.result()
    except Exception as e:
        print("SUBSCRIBE FAILED:", e)
        return
    # A reason code >= 128 means AWS refused (usually the IoT policy).
    if any(int(rc) >= 128 for rc in suback.reason_codes):
        print("SUBSCRIBE REFUSED by AWS:", suback.reason_codes)
        print("-> Add iot:Subscribe/iot:Receive for factory/* to your IoT policy "
              "(see policy/machineMonitor-Policy.json).")
    else:
        print("Subscribed to", TOPIC)


def on_disconnected(event):
    status["connected"] = False
    print("Disconnected from AWS IoT")


def on_failure(event):
    print("Connection failed:", event.exception)


# Build the MQTT client using the same certificate files as testmqttDemo.py.
client = mqtt5_client_builder.mtls_from_path(
    endpoint=ENDPOINT,
    cert_filepath=CERT_PATH,
    pri_key_filepath=KEY_PATH,
    ca_filepath=CA_PATH,
    client_id=CLIENT_ID,
    on_publish_received=on_message,
    on_lifecycle_connection_success=on_connected,
    on_lifecycle_connection_failure=on_failure,
    on_lifecycle_disconnection=on_disconnected,
)


# ---------------------------------------------------------------------------
# 4. FLASK PART  (the website)
# ---------------------------------------------------------------------------
app = Flask(__name__)


@app.route("/")
def index():
    """Serves the dashboard page (templates/dashboard.html)."""
    return render_template("dashboard.html")


@app.route("/api/data")
def api_data():
    """The web page calls this every 2 seconds to get fresh readings."""
    return jsonify(connected=status["connected"], readings=list(readings))


# ---------------------------------------------------------------------------
# 5. START EVERYTHING
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    client.start()   # connects to AWS in the background
    try:
        # use_reloader=False: otherwise Flask starts the script twice and we
        # would open two MQTT connections with the same client id.
        app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
    finally:
        client.stop()
