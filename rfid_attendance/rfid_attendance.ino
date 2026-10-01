/*
 * ==============================================================================
 * PROJECT: IoT RFID Attendance System
 * HARDWARE: ESP32 DevKit V1 + RC522 RFID Reader
 * 
 * WIRING:
 * RC522 SDA/SS  -> ESP32 GPIO 5 (D5)
 * RC522 SCK     -> ESP32 GPIO 18 (D18)
 * RC522 MOSI    -> ESP32 GPIO 23 (D23)
 * RC522 MISO    -> ESP32 GPIO 19 (D19)
 * RC522 IRQ     -> Not connected
 * RC522 GND     -> ESP32 GND
 * RC522 RST     -> ESP32 GPIO 22 (D22)
 * RC522 3.3V    -> ESP32 3V3 (⚠️ DO NOT CONNECT TO 5V)
 * 
 * REQUIRED ARDUINO LIBRARIES:
 * 1. MFRC522 by GithubCommunity
 * 2. ArduinoJson by Benoit Blanchon (v6 or v7)
 * ==============================================================================
 */

#include <SPI.h>
#include <MFRC522.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// -----------------------------------------------------------------------------
// NETWORK & SERVER CONFIGURATION
// Configure for your local Wi-Fi network and backend computer IP
// -----------------------------------------------------------------------------
const char* ssid     = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Computer's active Wi-Fi IPv4 address (Do NOT use localhost; use your local IP, e.g. 192.168.1.XX)
const char* serverUrl = "http://YOUR_SERVER_IP:8000/api/attendance/scan";

// -----------------------------------------------------------------------------
// HARDWARE PIN DEFINITIONS
// -----------------------------------------------------------------------------
#define SS_PIN  5    // ESP32 GPIO 5 connected to RC522 SDA/SS
#define RST_PIN 22   // ESP32 GPIO 22 connected to RC522 RST

MFRC522 rfid(SS_PIN, RST_PIN);

// Debounce helper to prevent immediate duplicate scans while holding card on reader
String lastScannedUID = "";
unsigned long lastScanTime = 0;
const unsigned long SCAN_COOLDOWN_MS = 2500; // 2.5 seconds cooldown

// -----------------------------------------------------------------------------
// SETUP
// -----------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println();
  Serial.println("================================");
  Serial.println("    RFID ATTENDANCE SYSTEM      ");
  Serial.println("================================");

  // 1. Initialize SPI bus & RC522 Reader
  SPI.begin();
  rfid.PCD_Init();
  delay(100);

  // 2. Connect to Wi-Fi
  Serial.print("Connecting to Wi-Fi: ");
  Serial.println(ssid);
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  delay(100);
  WiFi.begin(ssid, password);

  int wifiAttempts = 0;
  while (WiFi.status() != WL_CONNECTED && wifiAttempts < 40) {
    delay(500);
    Serial.print(".");
    wifiAttempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWi-Fi connected!");
    Serial.println("\nESP32 IP:");
    Serial.println(WiFi.localIP());
    Serial.println("\nBackend:");
    Serial.println(serverUrl);
  } else {
    Serial.println("\n[ERROR] Wi-Fi connection timed out!");
    Serial.println("Tip: ESP32 only supports 2.4GHz Wi-Fi ('Manasi B').");
  }

  Serial.println("\nRFID Reader Ready.");
  Serial.println("Waiting for card...\n");
}

// -----------------------------------------------------------------------------
// MAIN LOOP
// -----------------------------------------------------------------------------
void loop() {
  // Check if a new card is presented
  if (!rfid.PICC_IsNewCardPresent()) {
    return;
  }

  // Read card serial UID
  if (!rfid.PICC_ReadCardSerial()) {
    return;
  }

  // Format UID as uppercase colon-separated string: "CD:FA:02:07"
  String cardUID = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    if (rfid.uid.uidByte[i] < 0x10) {
      cardUID += "0";
    }
    cardUID += String(rfid.uid.uidByte[i], HEX);
    if (i < rfid.uid.size - 1) {
      cardUID += ":";
    }
  }
  cardUID.toUpperCase();

  // Prevent multiple spam triggers if card is held on the reader
  unsigned long now = millis();
  if (cardUID == lastScannedUID && (now - lastScanTime < SCAN_COOLDOWN_MS)) {
    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();
    return;
  }

  lastScannedUID = cardUID;
  lastScanTime = now;

  // Print detected card
  Serial.println("----------------------------------------");
  Serial.println("RFID CARD DETECTED!");
  Serial.print("UID: ");
  Serial.println(cardUID);

  // Send UID to FastAPI server via Wi-Fi HTTP POST
  sendUIDToServer(cardUID);

  // Halt PICC and stop crypto to prepare for next scan
  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
  delay(500);
}

// -----------------------------------------------------------------------------
// SEND CARD UID TO FASTAPI BACKEND
// -----------------------------------------------------------------------------
void sendUIDToServer(String uid) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("\nWi-Fi disconnected.");
    Serial.println("Attempting reconnection...");
    WiFi.reconnect();
    return;
  }

  Serial.println("\nSending attendance request...");
  Serial.println("\nPOST:");
  Serial.println(serverUrl);

  HTTPClient http;
  http.begin(serverUrl);
  http.addHeader("Content-Type", "application/json");

  // JSON payload format: {"card_uid": "CD:FA:02:07"}
  String jsonPayload = "{\"card_uid\":\"" + uid + "\"}";

  int httpCode = http.POST(jsonPayload);

  Serial.print("\nHTTP Response Code: ");
  Serial.println(httpCode);

  if (httpCode > 0) {
    String response = http.getString();
    Serial.println("\nServer Response:");
    Serial.println(response);

    // Parse JSON response
    #if ARDUINOJSON_VERSION_MAJOR >= 7
      JsonDocument doc;
    #else
      DynamicJsonDocument doc(1024);
    #endif

    DeserializationError error = deserializeJson(doc, response);

    if (error) {
      Serial.print("[ERROR] JSON parsing failed: ");
      Serial.println(error.c_str());
    } else {
      bool success = doc["success"] | false;
      bool attendanceMarked = doc["attendance_marked"] | false;
      bool alreadyMarked = doc["already_marked"] | false;

      if (success && attendanceMarked) {
        Serial.println("\nATTENDANCE MARKED");
        Serial.print("Student: ");
        Serial.println(doc["student"]["name"].as<const char*>());
        Serial.print("Serial No: ");
        Serial.println(doc["student"]["serial_number"].as<int>());
        Serial.println("Status: Present");
      } 
      else if (success && alreadyMarked) {
        Serial.println("\nATTENDANCE ALREADY MARKED");
        Serial.print("Student: ");
        Serial.println(doc["student"]["name"].as<const char*>());
        Serial.print("Serial No: ");
        Serial.println(doc["student"]["serial_number"].as<int>());
        Serial.println("Status: Present (Already marked today)");
      } 
      else {
        Serial.println("\nCARD NOT REGISTERED");
        Serial.println("Message: This RFID card is not registered to any student.");
      }
    }
  } else {
    Serial.println("\nHTTP request failed.");
    Serial.println("Check:");
    Serial.println("1. Wi-Fi connection");
    Serial.println("2. Backend IP address");
    Serial.println("3. Backend port (8000)");
    Serial.println("4. Backend running status");
    Serial.println("5. ESP32 and Computer connected to SAME Wi-Fi network");
    Serial.println("6. Windows Firewall blocking port 8000");
  }

  http.end();
  Serial.println("----------------------------------------\n");
}
