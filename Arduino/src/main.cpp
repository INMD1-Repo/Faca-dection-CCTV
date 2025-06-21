#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <Arduino.h>

const char* ssid = "Geoje_8080";
const char* password = "yong2048";
const char* mqtt_server = "192.168.0.9";
const int mqtt_port = 1883;

WiFiClient espClient;
PubSubClient client(espClient);

bool readyToConnect = false;
unsigned long lastPing = 0;

void callback(char* topic, byte* payload, unsigned int length);

void setup() {
  Serial.begin(9600); // Mega2560과 UART 통신
  Serial.println("ESP8266 Ready");

  // Mega2560에서 "CONNECT" 신호를 받을 때까지 대기
  String cmd = "";
  while (!readyToConnect) {
    if (Serial.available()) {
      cmd = Serial.readStringUntil('\n');
      cmd.trim();
      if (cmd == "CONNECT") readyToConnect = true;
    }
    delay(100);
  }

  Serial.println("Connecting WiFi...");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi Connected");

  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);

  Serial.println("Connecting MQTT...");
  while (!client.connected()) {
    client.connect("ESP8266Client");
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nMQTT Connected");
  client.subscribe("chatTopic");
}

void loop() {
  client.loop();

  // UART 연결 상태 확인 (Pong)
  if (Serial.available()) {
    String msg = Serial.readStringUntil('\n');
    msg.trim();
    if (msg.indexOf("Ping") >= 0) {
      Serial.println("Pong from ESP8266");
    }
  }

  // 2초마다 Ping 신호 전송 (테스트/상호확인용)
  if (millis() - lastPing > 2000) {
    Serial.println("Ping from ESP8266");
    lastPing = millis();
  }
}

// MQTT 메시지 수신 시 Mega2560으로 전송
void callback(char* topic, byte* payload, unsigned int length) {
  String msg;
  for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];
  Serial.println(msg); // Mega2560으로 전송
}