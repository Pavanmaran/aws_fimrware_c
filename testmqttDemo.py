import json, time, random, threading
from awscrt import mqtt5
from awsiot import mqtt5_client_builder

ENDPOINT = "a1dkr9puunhret-ats.iot.us-east-1.amazonaws.com"
CERT_PATH = "machineMonitor.cert.pem"
KEY_PATH = "machineMonitor.private.key"
CA_PATH = "root-CA.crt"
CLIENT_ID = "machineMonitor"
TOPIC = "factory/machine01/telemetry"

connection_success = threading.Event()

def on_lifecycle_connection_success(event):
    print("CONNECTED to AWS IoT")
    connection_success.set()

def on_lifecycle_connection_failure(event):
    print("CONNECTION FAILED:", event.exception)
    if event.connack_packet:
        print("CONNACK:", event.connack_packet)

client = mqtt5_client_builder.mtls_from_path(
    endpoint=ENDPOINT, cert_filepath=CERT_PATH,
    pri_key_filepath=KEY_PATH, ca_filepath=CA_PATH,
    client_id=CLIENT_ID,
    on_lifecycle_connection_success=on_lifecycle_connection_success,
    on_lifecycle_connection_failure=on_lifecycle_connection_failure)

client.start()
if not connection_success.wait(timeout=30):
    client.stop()
    raise SystemExit("Could not connect to AWS IoT within 30 seconds; check the certificate and attached IoT policy.")

temp = 32.0
try:
    while True:
        temp += random.uniform(-0.5, 0.5)
        vib = round(random.uniform(0.1, 0.6), 2)
        payload = {
            "device_id": CLIENT_ID,
            "temperature": round(temp, 1),
            "vibration": vib,
            "motor_status": "RUNNING",
            "ts": int(time.time())
        }

        pub_future = client.publish(mqtt5.PublishPacket(
            topic=TOPIC,
            payload=json.dumps(payload).encode(),
            qos=mqtt5.QoS.AT_LEAST_ONCE))

        pub_future.result(timeout=5)
        print("ACKED by AWS:", payload)
        time.sleep(2)
except KeyboardInterrupt:
    print("Stopping MQTT client...")
finally:
    client.stop()
