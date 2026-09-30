#include <Arduino.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>

const char* WIFI_SSID     = "YOUR_WIFI_NAME";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* AWS_ENDPOINT  = "a1dkr9puunhret-ats.iot.us-east-1.amazonaws.com";
const char* CLIENT_ID     = "machineMonitor";
const char* TOPIC         = "factory/machine01/telemetry";
constexpr uint8_t LIGHT_ADC_PIN = 34;

const char* AWS_CERT_CRT = R"EOF(
-----BEGIN CERTIFICATE-----
...paste contents of your file here...
-----END CERTIFICATE-----
)EOF";

const char* AWS_CERT_PRIVATE = R"EOF(
-----BEGIN RSA PRIVATE KEY-----
...paste contents of your file here...
-----END RSA PRIVATE KEY-----
)EOF";

const char* AWS_CERT_CA = R"EOF(
-----BEGIN CERTIFICATE-----
MIIDQTCCAimgAwIBAgITBmyfz5m/jAo54vB4ikPmljZbyjANBgkqhkiG9w0BAQsF
ADA5MQswCQYDVQQGEwJVUzEPMA0GA1UEChMGQW1hem9uMRkwFwYDVQQDExBBbWF6
b24gUm9vdCBDQSAxMB4XDTE1MDUyNjAwMDAwMFoXDTM4MDExNzAwMDAwMFowOTEL
MAkGA1UEBhMCVVMxDzANBgNVBAoTBkFtYXpvbjEZMBcGA1UEAxMQQW1hem9uIFJv
b3QgQ0EgMTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBALJ4gHHKeNXj
ca9HgFB0fW7Y14h29Jlo91ghYPl0hAEvrAIthtOgQ3pOsqTQNroBvo3bSMgHFzZM
9O6II8c+6zf1tRn4SWiw3te5djgdYZ6k/oI2peVKVuRF4fn9tBb6dNqcmzU5L/qw
IFAGbHrQgLKm+a/sRxmPUDgH3KKHOVj4utWp+UhnMJbulHheb4mjUcAwhmahRWa6
VOujw5H5SNz/0egwLX0tdHA114gk957EWW67c4cX8jJGKLhD+rcdqsq08p8kDi1L
93FcXmn/6pUCyziKrlA4b9v7LWIbxcceVOF34GfID5yHI9Y/QCB/IIDEgEw+OyQm
jgSubJrIqg0CAwEAAaNCMEAwDwYDVR0TAQH/BAUwAwEB/zAOBgNVHQ8BAf8EBAMC
AYYwHQYDVR0OBBYEFIQYzIU07LwMlJQuCFmcx7IQTgoIMA0GCSqGSIb3DQEBCwUA
A4IBAQCY8jdaQZChGsV2USggNiMOruYou6r4lK5IpDB/G/wkjUu0yKGX9rbxenDI
U5PMCCjjmCXPI6T53iHTfIUJrU6adTrCC2qJeHZERxhlbI1Bjjt/msv0tadQ1wUs
N+gDS63pYaACbvXy8MWy7Vu33PqUXHeeE6V/Uq2V8viTO96LXFvKWlJbYK8U90vv
o/ufQJVtMVT8QtPHRh8jrdkPSHCa2XV4cdFyQzR1bldZwgJcJmApzyMZFo6IQ6XU
5MsI+yMRQ+hDKXJioaldXgjUkK642M4UwtBV8ob2xJNDd2ZhwLnoQdeXeGADbkpy
rqXRfboQnoZsG4q5WTP468SQvvG5
-----END CERTIFICATE-----
)EOF";

WiFiClientSecure net;
PubSubClient client(net);

void connectWiFi() {
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println(" connected");
}

bool connectAWS() {
  net.setCACert(AWS_CERT_CA);
  net.setCertificate(AWS_CERT_CRT);
  net.setPrivateKey(AWS_CERT_PRIVATE);
  client.setServer(AWS_ENDPOINT, 8883);

  Serial.print("Connecting to AWS IoT");
  for (int attempt = 1; attempt <= 10; ++attempt) {
    if (client.connect(CLIENT_ID)) {
      Serial.println(" connected to AWS");
      return true;
    }
    Serial.printf("\nMQTT connect failed (attempt %d), state=%d\n", attempt, client.state());
    delay(2000);
  }
  Serial.println("AWS IoT connection failed; will retry later.");
  return false;
}

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);
  analogSetPinAttenuation(LIGHT_ADC_PIN, ADC_11db);
  connectWiFi();
  connectAWS();
}

void loop() {
  if (!client.connected()) {
    connectAWS();
  }
  client.loop();

  const int lightAdcRaw = analogRead(LIGHT_ADC_PIN);
  const float lightIntensityPct = (lightAdcRaw * 100.0f) / 4095.0f;

  char payload[160];
  snprintf(payload, sizeof(payload),
    "{\"device_id\":\"%s\",\"light_intensity_raw\":%d,\"light_intensity_pct\":%.1f}",
    CLIENT_ID, lightAdcRaw, lightIntensityPct);

  if (client.publish(TOPIC, payload)) {
    Serial.println(payload);
  } else {
    Serial.printf("MQTT publish failed, state=%d\n", client.state());
  }

  delay(2000);
}