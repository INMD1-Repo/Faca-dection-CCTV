#include <EEPROM.h>
#include <LiquidCrystal.h>
#include <openGLCD.h>
#include <fonts/SystemFont5x7.h>
#include <ArduinoJson.h>
#include "pitche.h" // pitches.h 파일 필요
#include <Arduino.h>

#define SPEAKER_PIN 57

LiquidCrystal lcd(44, 45, 46, 47, 48, 49);

#define EEPROM_ADDR 0
#define AUTH_LEN 8

// RGB LED 핀
int RGB_LED[] = {6, 7, 8}; // B, G, R
// 색상 테이블 (BGR)
int colors[7][3] = {
    {255, 255, 0},   // 노랑
    {255, 165, 0},   // 주황
    {255, 0, 0},     // 빨강
    {255, 0, 255},   // 보라
    {0, 255, 255},   // 하늘
    {127, 255, 255}, // 남색
    {207, 222, 189}  // 초록(핑크)
};

// 색상 설정 함수 (공통 애노드면 LOW=켜짐, 공통 캐소드면 HIGH=켜짐)
void setRGB(int r, int g, int b)
{
  analogWrite(RGB_LED[2], r); // R
  analogWrite(RGB_LED[1], g); // G
  analogWrite(RGB_LED[0], b); // B
}

// 승인음(간단한 멜로디)
void beepAccess()
{
  tone(SPEAKER_PIN, NOTE_C5, 320);
  delay(150);
  tone(SPEAKER_PIN, NOTE_E5, 320);
  delay(150);
  noTone(SPEAKER_PIN);
}

// 미승인 경고음(짧은 경고 3회)
void beepWarning()
{
  for (int i = 0; i < 3; i++)
  {
    tone(SPEAKER_PIN, NOTE_DS5, 300);
    delay(120);
    noTone(SPEAKER_PIN);
    delay(100);
  }
}

// 알림음(짧은 단음)
void beepNotice()
{
  tone(SPEAKER_PIN, NOTE_G5, 380);
  delay(100);
  noTone(SPEAKER_PIN);
}

void displayGLCDMessage(
    const String &typeStr,
    const String &timeStr,
    const String &nameStr,
    const String &etc1,
    const String &etc2,
    const String &etc3,
    const String &sendTime)
{
  GLCD.ClearScreen();
  GLCD.SelectFont(System5x7);

  GLCD.GotoXY(0, 0);
  GLCD.print("Type: ");
  GLCD.print(typeStr);
  GLCD.GotoXY(0, 8);
  GLCD.print("name: ");
  GLCD.print(nameStr);
  GLCD.GotoXY(0, 16);
  GLCD.print("Delivery message");
  GLCD.GotoXY(0, 24);
  GLCD.print(etc1);
  GLCD.GotoXY(0, 32);
  GLCD.print(etc2);
  GLCD.GotoXY(0, 40);
  GLCD.print(etc3);
  GLCD.GotoXY(0, 56);
  GLCD.print("보낸시각: ");
  GLCD.print(sendTime);
}

void setup()
{
  pinMode(SPEAKER_PIN, OUTPUT);
  for (int i = 0; i < 3; i++)
    pinMode(RGB_LED[i], OUTPUT);

  Serial.begin(115200);
  Serial1.begin(9600);
  lcd.begin(20, 4);

  GLCD.Init();
  GLCD.ClearScreen();
  GLCD.SelectFont(System5x7);

  char auth[AUTH_LEN + 1] = {0};
  for (int i = 0; i < AUTH_LEN; i++)
    auth[i] = EEPROM.read(EEPROM_ADDR + i);
  auth[AUTH_LEN] = '\0';

  if (strcmp(auth, "embenull") == 0)
  {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Auth Success");
    Serial.println("Auth Success");
    Serial1.println("CONNECT");
    GLCD.GotoXY(0, 0);
    GLCD.print("Waiting for MQTT...");
  }
  else
  {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Auth Failed");
    Serial.println("Auth Failed");
    GLCD.GotoXY(0, 0);
    GLCD.print("Auth Failed");
    setRGB(255, 0, 0); // 빨강(경고)
    while (1)
      ;
  }
}

void loop()
{
  static unsigned long lastPing = 0;
  static unsigned long lastUart = 0;
  static bool uartConnected = false;

  if (millis() - lastPing > 2000)
  {
    Serial1.println("Ping from Mega2560");
    lastPing = millis();
  }

  if (Serial1.available())
  {
    String msg = Serial1.readStringUntil('\n');
    msg.trim();
    lastUart = millis();

    if (msg.indexOf("Pong") >= 0 || msg.indexOf("Ping") >= 0)
    {
      uartConnected = true;
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("UART: Connected");
      lcd.setCursor(0, 1);
      lcd.print("Last: ");
      lcd.print(lastUart / 1000);
      lcd.print("s");
      setRGB(0, 0, 0); // 소등
    }
    else if (msg.length() > 0 && msg[0] == '{')
    {
      StaticJsonDocument<384> doc;
      DeserializationError error = deserializeJson(doc, msg);
      if (!error)
      {
        String typeStr = doc["Type"] | "";
        String timeStr = doc["time"] | "";
        String nameStr = doc["name"] | "";
        String etc1 = doc["etc1"] | "";
        String etc2 = doc["etc2"] | "";
        String etc3 = doc["etc3"] | "";
        String sendTime = doc["send_time"] | "";
        String notice = doc["notice"] | "";

        // RGB LED 표시
        if (typeStr == "access")
        {
          setRGB(255, 0, 0); // 빨강
          beepAccess();
        }
        else if (typeStr == "deaccess")
        {
          setRGB(127, 255, 255); // 남색
          beepWarning();
        }
        else if (typeStr == "notice")
        {
          setRGB(255, 255, 0); // 노랑
          beepNotice();
        }
        else
        {
          setRGB(0, 0, 0); // 소등
        }

        displayGLCDMessage(typeStr, timeStr, nameStr, etc1, etc2, etc3, sendTime);
        Serial.print("[ESP→GLCD] ");
        Serial.println(msg);

        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("UART: Connected");
        lcd.setCursor(0, 1);
        lcd.print("Last: ");
        lcd.print(lastUart / 1000);
        lcd.print("s");
      }
      else
      {
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("JSON Parse Error");
        Serial.print("[ERROR] JSON Parse: ");
        Serial.println(msg);
        setRGB(255, 0, 0); // 에러시 빨강
      }
    }
  }

  if (uartConnected && millis() - lastUart > 5000)
  {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("UART Disconnected");
    lcd.setCursor(0, 1);
    lcd.print("Last: ");
    lcd.print(lastUart / 1000);
    lcd.print("s");
    uartConnected = false;
    GLCD.ClearScreen();
    GLCD.GotoXY(0, 0);
    GLCD.print("UART Disconnected");
    setRGB(255, 0, 0); // 빨강
  }
}
