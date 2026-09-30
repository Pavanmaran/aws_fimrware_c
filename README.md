# ESP32 -> AWS IoT Core -> Flask Dashboard (beginner demo)

```
ESP32 (light sensor) --MQTT--> AWS IoT Core --MQTT--> dashboard/app.py (Flask) --> browser charts
```

## Folders
- `esp32/`      PlatformIO firmware: publishes light intensity to `factory/machine01/telemetry` every 2 s.
- `dashboard/`  Python + Flask app: subscribes to that topic and shows a live dashboard.
- `policy/`     AWS IoT policy (`machineMonitor-Policy.json`) - paste it into IoT Core -> Policies.
- `testmqttDemo.py`  Fake-data publisher for testing without the ESP32.

## Setup
1. **AWS IoT Core:** create a Thing + certificate, download the cert, private key and
   Amazon Root CA, attach the policy from `policy/`. Replace the account id / region in the policy with yours.
2. **Certificates:** put `machineMonitor.cert.pem`, `machineMonitor.private.key`, `root-CA.crt`
   in the repo root. They are git-ignored - **never commit them**.
3. **ESP32:** in `esp32/src/main.cpp` fill in Wi-Fi, endpoint and paste cert + private key, then upload with PlatformIO.
4. **Dashboard:**
   ```
   cd dashboard
   pip install -r requirements.txt
   python app.py
   ```
   Open http://localhost:5000

## Good to know
- Every MQTT client needs a unique client id (ESP32 = `machineMonitor`, dashboard = `basicPubSub`).
  Run only one dashboard at a time.
- Policy needs both `iot:Subscribe` and `iot:Receive` for the dashboard to get data.
