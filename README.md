# Smart-Presence-An-Integrated-RFID-and-Computer-Vision-Solution
---
## Overview
SmartPresence is an automated examination monitoring system that handles student attendance and washroom break tracking using dual-factor authentication (RFID card + face recognition), with built-in anti-cheating rules enforced in real time.

---

## System Architecture

    ESP32-CAM (Room 1) ──┐
    ESP32-CAM (Room 2) ──┤── WiFi (HTTP POST) ──► Raspberry Pi (Flask + SQLite)
    ESP32-CAM (Room 3) ──┤                                    │
    ESP32-CAM (Room 4) ──┘                                    ▼
                                                   Teacher / Admin Dashboard
                                                   (Browser, auto-refresh 5s)

---

## How It Works
1. Student taps RFID card on reader
2. ESP32-CAM captures photo simultaneously
3. Both sent to Raspberry Pi over WiFi
4. Server verifies face against stored encoding
5. Determines event type automatically:
   - First tap → Attendance marked
   - Already present + tap → Washroom exit
   - Currently outside + tap → Washroom re-entry
6. Anti-cheating rules checked (washroom exit only)
7. Result sent back → LED/buzzer feedback
8. Card updated with IN/OUT status

---

## Anti-Cheating Rules
- **Left Side (Room 1+2):** Max 2 students outside at once + no two students from same branch outside simultaneously
- **Right Side (Room 3+4):** Same rules, completely independent of left side

---

## Hardware

| Component | Qty | Purpose |
|---|---|---|
| ESP32-CAM (AI-Thinker) | 4 | WiFi node + camera |
| MFRC522 RFID module | 4 | Card read/write |
| MIFARE Classic 1K cards | 10+ | Student tokens |
| Raspberry Pi | 1 | Central server |
| Active buzzer + LEDs | 4 sets | Feedback per room |

### ESP32-CAM to MFRC522 Pin Mapping

| MFRC522 Pin | ESP32-CAM GPIO |
|---|---|
| VCC | 3.3V (NOT 5V) |
| GND | GND |
| SCK | GPIO 14 |
| MOSI | GPIO 13 |
| MISO | GPIO 12 |
| SS/SDA | GPIO 15 |
| RST | GPIO 2 |
| IRQ | Not connected |

---

## Software Stack
- **Server:** Python 3, Flask, SQLite
- **Face Recognition:** face_recognition (dlib), OpenCV
- **Firmware:** Arduino C++ (ESP32-CAM)
- **Dashboard:** HTML, CSS, JavaScript (Jinja2 templates)

---

## Database Schema

| Table | Purpose |
|---|---|
| students | UID, face_encoding BLOB, branch, room |
| teachers | Login credentials, room assignment |
| attendance | Date-keyed entry records per student |
| live_movement | Real-time outside tracking (NULL in_time = currently out) |
| scan_log | Complete audit trail of every scan event |

---

## Features
- Dual-factor authentication (RFID + face recognition)
- Automatic event detection (attendance / washroom out / washroom in)
- Side-wise anti-cheating rule enforcement
- Room-filtered teacher dashboard with 5-second auto-refresh
- Admin panel with Left/Right side tabs and room sub-tabs
- Washroom duration tracking
- CSV export for attendance and washroom logs
- RFID card write-back (IN/OUT status to MIFARE Sector 0)
- Complete scan audit log for post-exam review

---

## Project Structure

    smartpresence/
    ├── app.py                    # Flask server (all routes)
    ├── database.py               # DB helper functions
    ├── rules.py                  # Anti-cheating rule engine
    ├── face_module.py            # Face recognition module
    ├── schema.sql                # Database schema (5 tables)
    ├── enroll_student.py         # Student enrollment script
    ├── templates/
    │   ├── login.html            # Teacher login page
    │   ├── dashboard.html        # Live room dashboard
    │   └── admin.html            # Admin panel
    └── esp32_firmware/
        └── smartpresence/
            └── smartpresence.ino # Arduino firmware

---

## Setup

### Raspberry Pi

    # Create virtual environment
    python3 -m venv ~/smartpresence-env
    source ~/smartpresence-env/bin/activate

    # Install dependencies
    pip install flask numpy opencv-python-headless dlib face-recognition

    # Initialize database
    cd "smartpresence"
    python3 -c "from database import init_db; init_db()"

    # Run server
    python3 app.py

### ESP32-CAM Firmware
1. Open `smartpresence.ino` in Arduino IDE
2. Update these values at the top of the file:

        const char* WIFI_SSID     = "YOUR_WIFI_NAME";
        const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
        const char* SERVER_URL    = "http://PI_IP:5000/api/scan";
        const int   ROOM_ID       = 1;  // 1, 2, 3, or 4

3. Select board: Tools → Board → AI Thinker ESP32-CAM
4. Connect GPIO 0 to GND (flash mode)
5. Upload code → disconnect GPIO 0 → restart board

### Student Enrollment

    source ~/smartpresence-env/bin/activate
    python3 enroll_student.py
    # Option 1: Single student enrollment
    # Option 2: Bulk enrollment from CSV file

---

## Default Login Credentials

| Role | Username | Password | Access |
|---|---|---|---|
| Admin | admin | admin123 | All rooms + export |
| Teacher 1 | teacher1 | pass1 | Room 1 only |
| Teacher 2 | teacher2 | pass2 | Room 2 only |
| Teacher 3 | teacher3 | pass3 | Room 3 only |
| Teacher 4 | teacher4 | pass4 | Room 4 only |

---

## Test Results
Tested with 10 students across 4 rooms simultaneously:

| Test Scenario | Result |
|---|---|
| Attendance marking (first tap) | Working |
| Washroom exit (second tap) | Working |
| Washroom re-entry (third tap) | Working |
| Same branch denial | Working |
| Max 2 outside denial | Working |
| Face mismatch denial | Working |
| Dashboard live update | Working |
| Admin panel tabs | Working |
| CSV export | Working |

---

## Important Notes
- MFRC522 requires 3.3V only — 5V will permanently damage the chip
- ESP32-CAM needs a dedicated 5V/2A adapter for stable operation — do not power from FTDI
- Use plastic enclosure only — metal blocks RFID radio signal
- GPIO 0 should be connected to GND only during code upload, remove after upload is done
- Every new terminal session on Raspberry Pi requires virtual environment activation

---

## Supervisor
**Dr. Sumit Gautam**
Department of Electrical Engineering
Indian Institute of Technology Indore
