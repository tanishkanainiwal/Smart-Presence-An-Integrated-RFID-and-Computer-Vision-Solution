#include <WiFi.h>
#include <HTTPClient.h>
#include <SPI.h>
#include <MFRC522.h>
#include "esp_camera.h"

// Change these 3 things
const char* WIFI_SSID     = "realme 9 Pro 5G";
const char* WIFI_PASSWORD = "khushi123";
const char* SERVER_URL    = "http://10.153.40.206:5000/api/scan";
const int   ROOM_ID       = 3;

// RFID pins
#define RFID_RST_PIN   2
#define RFID_SS_PIN    15

// Feedback pins
#define GREEN_LED_PIN  4
#define RED_LED_PIN    33
#define BUZZER_PIN     16

// Camera pins (AI-Thinker)
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

MFRC522 rfid(RFID_SS_PIN, RFID_RST_PIN);
MFRC522::MIFARE_Key rfidKey;

void setup() {
    Serial.begin(115200);
    delay(500);
    Serial.println("\n\n=== SmartPresence ESP32-CAM ===");
    Serial.print("Room ID: ");
    Serial.println(ROOM_ID);

    pinMode(GREEN_LED_PIN, OUTPUT);
    pinMode(RED_LED_PIN,   OUTPUT);
    pinMode(BUZZER_PIN,    OUTPUT);
    digitalWrite(GREEN_LED_PIN, LOW);
    digitalWrite(RED_LED_PIN,   LOW);
    digitalWrite(BUZZER_PIN,    LOW);

    for (byte i = 0; i < 6; i++) {
        rfidKey.keyByte[i] = 0xFF;
    }



     if (!initCamera()) {
        Serial.println("Camera init failed!");
        // Red LED blink ,indicate karne ke liye
        for (int i = 0; i < 5; i++) {
            digitalWrite(RED_LED_PIN, HIGH);
            delay(300);
            digitalWrite(RED_LED_PIN, LOW);
            delay(300);
        }
    } else {
        Serial.println("Camera ready");
    }

     delay(1000);
    // // Camera temporarily disabled for testing
    // Serial.println("Camera skipped for now");

    SPI.begin(14, 12, 13, 15);
    rfid.PCD_Init();
    Serial.println("RFID reader ready");

delay(500);

    connectWiFi();

    Serial.println("\n System ready — Card tap karo...\n");
}

void loop() {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("WiFi disconnected! Reconnecting...");
        connectWiFi();
        return;
    }

    if (!rfid.PICC_IsNewCardPresent()) {
        delay(100);
        return;
    }

    if (!rfid.PICC_ReadCardSerial()) {
        delay(100);
        return;
    }

    String uid = getUID();
    Serial.println("━━━━━━━━━━━━━━━━━━━━━━━━");
    Serial.print("Card detected! UID: ");
    Serial.println(uid);

    // Photo/server temporarily skipped for testing
    // Serial.println("Card read successful! (Photo/server skipped for testing)");
    // showAllowed(1);

  // Photo lo
    Serial.println("Capturing photo...");
    camera_fb_t* fb = capturePhoto();

    if (!fb) {
        Serial.println("Photo capture failed!");
        showDenied();
        rfid.PICC_HaltA();
        rfid.PCD_StopCrypto1();
        return;
    }

    Serial.print(" Photo captured: ");
    Serial.print(fb->len);
    Serial.println("bytes");

    // Server ko bhejo
    Serial.println("Sending to server...");
    String response = sendToServer(uid, fb->buf, fb->len);

    // Camera buffer free karo
    esp_camera_fb_return(fb);

    // Response handle karo
    handleResponse(response, uid);

    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();

    delay(2000);
    Serial.println("Ready for next card...\n");
}

bool initCamera() {
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.pin_d0       = Y2_GPIO_NUM;
    config.pin_d1       = Y3_GPIO_NUM;
    config.pin_d2       = Y4_GPIO_NUM;
    config.pin_d3       = Y5_GPIO_NUM;
    config.pin_d4       = Y6_GPIO_NUM;
    config.pin_d5       = Y7_GPIO_NUM;
    config.pin_d6       = Y8_GPIO_NUM;
    config.pin_d7       = Y9_GPIO_NUM;
    config.pin_xclk     = XCLK_GPIO_NUM;
    config.pin_pclk     = PCLK_GPIO_NUM;
    config.pin_vsync    = VSYNC_GPIO_NUM;
    config.pin_href     = HREF_GPIO_NUM;
    config.pin_sscb_sda = SIOD_GPIO_NUM;
    config.pin_sscb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn     = PWDN_GPIO_NUM;
    config.pin_reset    = RESET_GPIO_NUM;
    config.xclk_freq_hz = 10000000;
    config.pixel_format = PIXFORMAT_JPEG;
    config.frame_size   = FRAMESIZE_VGA;
    config.jpeg_quality = 15;
    config.fb_count     = 1;
    config.fb_location  = CAMERA_FB_IN_DRAM;

    return esp_camera_init(&config) == ESP_OK;
}

camera_fb_t* capturePhoto() {
    camera_fb_t* fb = esp_camera_fb_get();
    esp_camera_fb_return(fb);
    fb = esp_camera_fb_get();
    esp_camera_fb_return(fb);
    fb = esp_camera_fb_get();
    return fb;
}

String getUID() {
    String uid = "";
    for (byte i = 0; i < rfid.uid.size; i++) {
        if (rfid.uid.uidByte[i] < 0x10) uid += "0";
        uid += String(rfid.uid.uidByte[i], HEX);
    }
    uid.toUpperCase();
    return uid;
}

// String sendToServer(String uid, uint8_t* imageData, size_t imageLen) {
//     HTTPClient http;
//     http.begin(SERVER_URL);
//     http.setTimeout(20000);

//     String boundary = "SmartPresenceBoundary123";
//     String contentType = "multipart/form-data; boundary=" + boundary;
//     http.addHeader("Content-Type", contentType);

//     String bodyStart = "";
//     bodyStart += "--" + boundary + "\r\n";
//     bodyStart += "Content-Disposition: form-data; name=\"uid\"\r\n\r\n";
//     bodyStart += uid + "\r\n";
//     bodyStart += "--" + boundary + "\r\n";
//     bodyStart += "Content-Disposition: form-data; name=\"room_id\"\r\n\r\n";
//     bodyStart += String(ROOM_ID) + "\r\n";
//     bodyStart += "--" + boundary + "\r\n";
//     bodyStart += "Content-Disposition: form-data; name=\"image\"; filename=\"photo.jpg\"\r\n";
//     bodyStart += "Content-Type: image/jpeg\r\n\r\n";

//     String bodyEnd = "\r\n--" + boundary + "--\r\n";

//     int totalLen = bodyStart.length() + imageLen + bodyEnd.length();
//     uint8_t* requestBody = (uint8_t*)malloc(totalLen);
//     if (!requestBody) {
//         Serial.println("Memory allocation failed!");
//         return "";
//     }

//     memcpy(requestBody, bodyStart.c_str(), bodyStart.length());
//     memcpy(requestBody + bodyStart.length(), imageData, imageLen);
//     memcpy(requestBody + bodyStart.length() + imageLen, bodyEnd.c_str(), bodyEnd.length());


// Serial.print("Free heap before POST: ");
// Serial.println(ESP.getFreeHeap());
//     int httpCode = http.POST(requestBody, totalLen);
//     free(requestBody);

//     String response = "";
//     if (httpCode == 200) {
//         response = http.getString();
//         Serial.print("Server response: ");
//         Serial.println(response);
//     } else {
//         Serial.print("HTTP Error: ");
//         Serial.println(httpCode);
//     }

//     http.end();
//     return response;
// }


String sendToServer(String uid, uint8_t* imageData, size_t imageLen) {
    WiFiClient client;

    // Extract host and port from SERVER_URL manually
    String url = String(SERVER_URL);
    String host;
    int port = 80;
    String path = "/api/scan";

    int protoEnd = url.indexOf("://") + 3;
    int pathStart = url.indexOf("/", protoEnd);
    String hostPort = url.substring(protoEnd, pathStart);
    path = url.substring(pathStart);

    int colonIdx = hostPort.indexOf(":");
    if (colonIdx >= 0) {
        host = hostPort.substring(0, colonIdx);
        port = hostPort.substring(colonIdx + 1).toInt();
    } else {
        host = hostPort;
    }

    Serial.print("Connecting to host: ");
    Serial.print(host);
    Serial.print(" port: ");
    Serial.println(port);

    if (!client.connect(host.c_str(), port)) {
        Serial.println("Connection to server failed");
        return "";
    }

    String boundary = "SmartPresenceBoundary123";

    String bodyStart = "";
    bodyStart += "--" + boundary + "\r\n";
    bodyStart += "Content-Disposition: form-data; name=\"uid\"\r\n\r\n";
    bodyStart += uid + "\r\n";
    bodyStart += "--" + boundary + "\r\n";
    bodyStart += "Content-Disposition: form-data; name=\"room_id\"\r\n\r\n";
    bodyStart += String(ROOM_ID) + "\r\n";
    bodyStart += "--" + boundary + "\r\n";
    bodyStart += "Content-Disposition: form-data; name=\"image\"; filename=\"photo.jpg\"\r\n";
    bodyStart += "Content-Type: image/jpeg\r\n\r\n";

    String bodyEnd = "\r\n--" + boundary + "--\r\n";

    size_t totalLen = bodyStart.length() + imageLen + bodyEnd.length();

    // HTTP headers manually likho
    client.print("POST " + path + " HTTP/1.1\r\n");
    client.print("Host: " + host + "\r\n");
    client.print("Content-Type: multipart/form-data; boundary=" + boundary + "\r\n");
    client.print("Content-Length: " + String(totalLen) + "\r\n");
    client.print("Connection: close\r\n\r\n");

    // Body ko chunks mein bhejo
    client.print(bodyStart);

    // Image data ko chhote chunks mein bhejo (1024 bytes ek baar mein)
    size_t chunkSize = 1024;
    size_t sent = 0;
    while (sent < imageLen) {
        size_t toSend = min(chunkSize, imageLen - sent);
        client.write(imageData + sent, toSend);
        sent += toSend;
        delay(1);  // Thoda breathing room WiFi stack ko
    }

    client.print(bodyEnd);

    Serial.println("Request sent, waiting for response...");

    // Response ka wait karo (timeout ke saath)
    unsigned long timeout = millis();
    while (client.connected() && !client.available()) {
        if (millis() - timeout > 15000) {
            Serial.println("Response timeout");
            client.stop();
            return "";
        }
        delay(10);
    }

    // Response padho
    String response = "";
    bool headersDone = false;
    while (client.available()) {
        String line = client.readStringUntil('\n');
        if (!headersDone) {
            if (line == "\r") {
                headersDone = true;
            }
        } else {
            response += line + "\n";
        }
    }

    client.stop();

    Serial.print("Server response: ");
    Serial.println(response);

    return response;
}

void handleResponse(String response, String uid) {
    if (response == "") {
        Serial.println("No response from server");
        showDenied();
        return;
    }

    if (response.indexOf("\"ALLOWED\"") >= 0) {
        if (response.indexOf("ATTENDANCE") >= 0) {
            Serial.println("ATTENDANCE marked!");
            writeToCard("IN ");
            showAllowed(1);
        } else if (response.indexOf("WASHROOM_OUT") >= 0) {
            Serial.println("WASHROOM OUT allowed!");
            writeToCard("OUT");
            showAllowed(2);
        } else if (response.indexOf("WASHROOM_IN") >= 0) {
            Serial.println("WASHROOM IN — Welcome back!");
            writeToCard("IN ");
            showAllowed(1);
        }
    } else {
        if (response.indexOf("DENIED_FACE_MISMATCH") >= 0) {
            Serial.println("DENIED: Face match failed!");
        } else if (response.indexOf("DENIED_SAME_BRANCH") >= 0) {
            Serial.println("DENIED: Same branch outside!");
        } else if (response.indexOf("DENIED_MAX_LIMIT") >= 0) {
            Serial.println("DENIED: Max 2 students outside!");
        } else if (response.indexOf("DENIED_UNKNOWN_CARD") >= 0) {
            Serial.println("DENIED: Card not registered!");
        } else {
            Serial.println("DENIED: Unknown reason");
        }
        showDenied();
    }
}

void writeToCard(String status) {
    byte blockNum = 1;
    byte dataBlock[16] = {
        ' ',' ',' ',' ',' ',' ',' ',' ',
        ' ',' ',' ',' ',' ',' ',' ',' '
    };

    for (int i = 0; i < status.length() && i < 16; i++) {
        dataBlock[i] = status[i];
    }

    MFRC522::StatusCode authStatus = rfid.PCD_Authenticate(
        MFRC522::PICC_CMD_MF_AUTH_KEY_A, blockNum, &rfidKey, &(rfid.uid));

    if (authStatus != MFRC522::STATUS_OK) {
        Serial.println("Card authentication failed!");
        return;
    }

    MFRC522::StatusCode writeStatus = rfid.MIFARE_Write(blockNum, dataBlock, 16);

    if (writeStatus == MFRC522::STATUS_OK) {
        Serial.print("Card updated: ");
        Serial.println(status);
    } else {
        Serial.println("Card write failed!");
    }
}

void connectWiFi() {
    WiFi.mode(WIFI_STA);
    WiFi.setTxPower(WIFI_POWER_8_5dBm);
    delay(100);

    Serial.print("Connecting to WiFi: ");
    Serial.println(WIFI_SSID);

    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        Serial.print(".");
        attempts++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n WiFi connected!");
        Serial.print("IP: ");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println("\n WiFi failed! Retrying in 5 sec...");
        delay(5000);
        connectWiFi();
    }
}

void showAllowed(int beepCount) {
    digitalWrite(RED_LED_PIN,   LOW);
    digitalWrite(GREEN_LED_PIN, HIGH);
    for (int i = 0; i < beepCount; i++) {
        digitalWrite(BUZZER_PIN, HIGH);
        delay(200);
        digitalWrite(BUZZER_PIN, LOW);
        delay(150);
    }
    delay(1500);
    digitalWrite(GREEN_LED_PIN, LOW);
}

void showDenied() {
    digitalWrite(GREEN_LED_PIN, LOW);
    digitalWrite(RED_LED_PIN,   HIGH);
    for (int i = 0; i < 3; i++) {
        digitalWrite(BUZZER_PIN, HIGH);
        delay(100);
        digitalWrite(BUZZER_PIN, LOW);
        delay(100);
    }
    delay(1500);
    digitalWrite(RED_LED_PIN, LOW);
}