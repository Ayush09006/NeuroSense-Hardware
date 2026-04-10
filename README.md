# NeuroSense v2.1 — Full System Documentation

> **Parkinson's Tremor Detection & Clinical Monitoring System**  
> A wearable biosensor glove + cloud backend for objective, real-time UPDRS tremor assessment.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Hardware Components](#2-hardware-components)
3. [Firmware Architecture (ESP32)](#3-firmware-architecture-esp32)
4. [Backend Architecture (Django)](#4-backend-architecture-django)
5. [Database Models](#5-database-models)
6. [API Endpoints](#6-api-endpoints)
7. [Doctor Dashboard — Full Specification](#7-doctor-dashboard--full-specification)
8. [Signal Processing Pipeline](#8-signal-processing-pipeline)
9. [UPDRS Tremor Classification](#9-updrs-tremor-classification)
10. [Calibration Procedure](#10-calibration-procedure)
11. [Project File Structure](#11-project-file-structure)
12. [Setup & Running Locally](#12-setup--running-locally)
13. [Connecting Your ESP32](#13-connecting-your-esp32)
14. [Known Limitations & Future Work](#14-known-limitations--future-work)

---

## 1. System Overview

NeuroSense is a real-time clinical tool designed to help neurologists objectively quantify Parkinson's Disease tremors. The system uses a wearable IMU + EMG sensor glove (ESP32 + MPU6050) to stream motion and muscle data wirelessly to a Django backend, which a clinician monitors live on the **Doctor Dashboard**.

```
┌──────────────────────┐        WiFi / HTTP POST        ┌──────────────────────┐
│   ESP32 Glove Node   │  ─────────────────────────────▶│  Django REST Backend │
│                      │   JSON payload @ 5 Hz           │  (Windows / Linux)   │
│  • MPU6050 (IMU)     │                                 │  • SQLite Database   │
│  • EMG Electrode     │                                 │  • REST API          │
│  • 50 Hz sampling    │                                 │  • Doctor Dashboard  │
└──────────────────────┘                                 └──────────────────────┘
                                                                    │
                                                         Browser (Chart.js)
                                                                    │
                                                         ┌──────────────────────┐
                                                         │   Doctor Dashboard   │
                                                         │  • Live FFT Charts   │
                                                         │  • UPDRS Classifier  │
                                                         │  • PDF Report Export │
                                                         └──────────────────────┘
```

---

## 2. Hardware Components

| Component | Role | Specification |
|-----------|------|---------------|
| **ESP32 Dev Board** | Main microcontroller + WiFi | Dual-core 240 MHz, 802.11 b/g/n |
| **MPU6050** | 6-axis IMU (Accel + Gyro) | ±8g accelerometer, ±500 °/s gyro |
| **EMG Electrode** | Muscle activation sensor | Analog signal on GPIO 32, 12-bit ADC |
| **I²C Bus** | IMU communication | SDA → GPIO 25 · SCL → GPIO 26 |
| **USB / LiPo** | Power supply | 3.3V regulated |

### Wiring
```
MPU6050 VCC  → ESP32 3.3V
MPU6050 GND  → ESP32 GND
MPU6050 SDA  → ESP32 GPIO 25
MPU6050 SCL  → ESP32 GPIO 26

EMG Signal   → ESP32 GPIO 32
EMG GND      → ESP32 GND
```

---

## 3. Firmware Architecture (ESP32)

**File:** `neurosense_firmware/neurosense_firmware.ino`

The firmware is organized into five self-contained namespaces:

### 3.1 Config Namespace
Holds all compile-time constants. Change WiFi credentials and server IP here:
```cpp
constexpr char SSID[]         = "YourWiFiName";
constexpr char PASSWORD[]     = "YourWiFiPassword";
constexpr char API_ENDPOINT[] = "http://<YOUR_PC_IP>:8000/api/sensor-data/";
constexpr uint32_t SAMPLE_INTERVAL_MS = 20;   // 50 Hz internal sampling
constexpr uint32_t SEND_INTERVAL_MS   = 200;  // 5 Hz transmission to server
```

### 3.2 EMG Namespace — 3-Stage Signal Pipeline
```
Raw ADC (12-bit, 0–4095)
        │
        ▼
[Stage 1] Moving Average Filter (32-tap MA)
        → Smooths high-frequency electrical noise from ADC
        │
        ▼
[Stage 2] IIR High-Pass Filter (α=0.9274, cutoff ~10 Hz)
        → Removes slow DC drift and motion baseline
        │
        ▼
[Stage 3] RMS Envelope (50-sample window = 1 second)
        → Gives a stable energy metric of muscle contraction
        → Output: emg_rms, emg_rms_percent (0–100%)
```

**Key Fix (v2.1):** RMS buffer now recomputes the full sum of squares each sample
to avoid floating-point drift that caused the RMS to go negative over time.

### 3.3 IMU Namespace — Calibration + Complementary Filter
- Reads accelerometer (m/s²) and gyroscope (rad/s) from MPU6050
- On boot, **averages 512 samples** to build a full gravity vector offset
- Subtracts offsets from every live reading → gravity-free motion signal
- Applies a **Complementary Filter** (α=0.96) to fuse accel + gyro into stable Roll/Pitch angles

### 3.4 WiFiNet Namespace — Connection Manager
- State machine: `DISCONNECTED → CONNECTING → CONNECTED`
- Auto-reconnects after WiFi loss
- Times out after 15 seconds and retries

### 3.5 Payload Namespace — JSON Serializer
Builds the JSON body sent to the backend:
```json
{
  "device_id": "ESP32_NODE_01",
  "ts_ms": 12345,
  "emg": {
    "raw": 1820,
    "ma_filtered": 1815,
    "hp_filtered": "12.45",
    "rms": "18.30",
    "rms_percent": "0.447",
    "voltage": "1.4638"
  },
  "imu": {
    "valid": true,
    "calibrated": true,
    "accel": { "x": "0.0120", "y": "-0.0080", "z": "0.0031" },
    "gyro":  { "x": "0.00120", "y": "-0.00050", "z": "0.00030" },
    "roll": "5.230",
    "pitch": "-2.100",
    "temp_c": "31.50"
  },
  "wifi_rssi": -62
}
```

### Main Loop (Non-blocking, millis() driven)
```
Every 20ms  → Sample EMG + IMU (50 Hz)
Every 200ms → Build JSON and POST to Django API (5 Hz)
Every 10s   → Print heap diagnostics to Serial
Always      → Maintain WiFi connection state machine
```

---

## 4. Backend Architecture (Django)

**Framework:** Django 5.0.1 + Django REST Framework  
**Database:** SQLite (development) → upgrade to PostgreSQL for production  
**Static files:** Bootstrap 5.3.3 (CDN) · Chart.js (CDN) · Font: Inter

### Apps
```
biosensor_backend/          ← Django project settings
biosensor_api/              ← Main application
    models.py               ← Database schema
    views.py                ← All view logic (API + HTML pages)
    urls.py                 ← URL routing
    serializers.py          ← DRF serializers
    templates/
        login.html          ← Doctor login page
        register.html       ← Doctor signup page
        doctor_dashboard.html ← Main clinical monitoring dashboard
        patient_list.html   ← Patient register
        patient_form.html   ← Add new patient
        patient_detail.html ← Individual patient records
```

---

## 5. Database Models

### Patient
| Field | Type | Description |
|-------|------|-------------|
| `name` | CharField | Full patient name |
| `age` | IntegerField | Age in years |
| `gender` | CharField | M / F / Other |
| `patient_id` | CharField (unique) | Hospital MRN / ID (e.g. `MRN-A3K92P`) |
| `diagnosis` | TextField | Clinical notes on diagnosis |
| `doctor` | FK → User | Which clinician owns this record |
| `created_at` | DateTimeField | Auto-set on creation |

### SensorReading
Each row = one data frame sent by the ESP32 (arrives at ~5 Hz).

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| `device_id` | CharField | — | Firmware device identifier |
| `ts_ms` | BigIntegerField | ms | ESP32 `millis()` timestamp |
| `timestamp` | DateTimeField | — | Server-side receipt time (auto) |
| `emg_raw` | IntegerField | ADC counts | Raw 12-bit ADC value (0–4095) |
| `emg_rms` | FloatField | ADC counts | RMS envelope value |
| `emg_rms_pct` | FloatField | % (0–100) | RMS as % of full ADC scale |
| `emg_voltage` | FloatField | Volts | Reconstructed voltage (×3.3/4095) |
| `acc_x/y/z` | FloatField | LSB | Accel stored as MPU6050 LSB units |
| `gyro_x/y/z` | FloatField | LSB | Gyro stored as MPU6050 LSB units |
| `roll` | FloatField | degrees | Arm roll angle |
| `pitch` | FloatField | degrees | Arm pitch angle |
| `imu_temp` | FloatField | °C | IMU chip temperature |
| `imu_calibrated` | BooleanField | — | True once firmware calibration ran |
| `wifi_rssi` | IntegerField | dBm | WiFi signal strength |

> **LSB Conversion constants used in dashboard JS:**  
> `ACC_LSB = 16384` (MPU6050 ±2g range → 1g = 16384 LSB)  
> `GYRO_LSB = 131` (MPU6050 ±250°/s range)  
> `G = 9.81 m/s²`

### TestSession
Stores a summary record after each clinical session ends.

| Field | Description |
|-------|-------------|
| `patient` | FK → which patient was assessed |
| `doctor` | FK → which clinician ran the session |
| `started_at / ended_at` | Session timestamps |
| `avg_emg_voltage` | Mean muscle activation across session |
| `avg_acc_mag` | Mean tremor amplitude magnitude |
| `tremor_score` | Composite score for clinical records |

---

## 6. API Endpoints

| Method | URL | Description | Used By |
|--------|-----|-------------|---------|
| `POST` | `/api/sensor-data/` | Ingest a data frame from ESP32 | ESP32 Firmware |
| `GET` | `/api/sensor-data/list/?limit=200` | Fetch last N readings (JSON) | Dashboard JS |
| `GET` | `/api/patients/` | List all patients (JSON) | Dashboard patient switcher |
| `GET` | `/api/patients/<id>/` | Single patient details | Dashboard |
| `GET` | `/` | Doctor login page | Browser |
| `GET/POST` | `/register/` | Doctor signup | Browser |
| `GET` | `/doctor-dashboard/` | Main clinical dashboard | Browser |
| `GET` | `/patients/` | Patient list HTML page | Browser |
| `GET/POST` | `/patients/add/` | Add new patient form | Browser |

---

## 7. Doctor Dashboard — Full Specification

**URL:** `http://<server>:8000/doctor-dashboard/`

The dashboard is a single-page app driven entirely by JavaScript. It polls the backend every 1 second during a session, processes all sensor data client-side, and renders live charts.

### 7.1 Pre-Session (Live Preview Mode)
Before starting a session, the dashboard polls every 2 seconds and shows:
- **Connection dot** → green "Live" / red "Disconnected"
- **Live Gyro Magnitude** → rotational activity in °/s (is the sensor on and moving?)
- **Live EMG %** → muscle activation sanity check before strapping on the glove

### 7.2 Patient Selector
- Dropdown populated from `GET /api/patients/`
- Select a patient to inject their name, ID, and age into the report header
- Changing the patient resets the session cleanly

### 7.3 Session Control
| Control | Function |
|---------|----------|
| **Start Monitoring** | Begins a 120-second timed session. Resets all session data + calibration flags |
| **Stop** | Instantly ends the session. Freezes charts on final values |
| **Countdown timer** | Live `MM:SS` clock counting down from `02:00` |
| **Generate Report** | Exports a PDF-ready clinical report with all charts |

### 7.4 Clinical Metrics Cards (updated every second)

| Card | Value | Description |
|------|-------|-------------|
| **UPDRS Score** | 0–4 | Unified Parkinson's Disease Rating Scale tremor item |
| **Tremor Amplitude** | m/s² | RMS of gravity-compensated 3-axis acceleration magnitude |
| **Dominant Frequency** | Hz | Peak tremor frequency from FFT (EMA-smoothed) |
| **Tremor Type** | Absent / Rest / Essential / Action | Classified from frequency + amplitude thresholds |
| **EMG Activity** | % (0–100) | Muscle contraction energy as % of ADC full scale |
| **Gyro Magnitude** | °/s | Total rotational velocity of the hand/wrist |
| **Roll / Pitch** | degrees | Arm orientation angles |
| **IMU Temp** | °C | MPU6050 chip temperature (drift indicator) |

### 7.5 Live Charts

#### Chart 1 — FFT Spectrum (Frequency Domain)
- **X-axis:** Frequency bins (Hz), 0 to Nyquist
- **Y-axis:** Spectral amplitude (m/s²)
- **Window:** Last 50 data frames (10 seconds at 5 Hz)
- **Processing:** Hann-windowed DFT with DC suppression and mean detrending
- **Peak:** Highlighted with EMA smoothing (α=0.15) to reject motion transients

#### Chart 2 — Tremor Amplitude (Time Domain)
- **X-axis:** Time into session (seconds)
- **Y-axis:** Amplitude magnitude m/s² (auto-scaling)
- **Data:** All session samples from `sessionStart` to now
- **Formula:** `√( (ax−gBase.x)² + (ay−gBase.y)² + (az−gBase.z)² )`

#### Chart 3 — EMG Activity (Bar Chart)
- **X-axis:** Time (last 20 samples, ~4 seconds)
- **Y-axis:** EMG RMS % (0–100%)
- **Color:** Teal bars when above 5% (active contraction), grey when at rest

#### Chart 4 — Axis Decomposition (Multi-line)
- **X-axis:** Time (last 30 samples)
- **Y-axis:** Acceleration in m/s² (auto-scaling, after gravity removal)
- **Lines:** X (blue) · Y (green) · Z (red) acceleration components
- Shows which axis is dominant in the tremor pattern

### 7.6 Session Stats Panel
- Total samples collected
- Average tremor amplitude across the full session
- Dominant tremor frequency (smoothed)

### 7.7 Raw Data Table
Collapsible table showing last 100 readings:

| Column | Unit | Source |
|--------|------|--------|
| Time | HH:MM:SS | `timestamp` / `created_at` |
| EMG RMS % | % | `emg_rms_pct` |
| Acc X | m/s² | Gravity-compensated |
| Acc Y | m/s² | Gravity-compensated |
| Acc Z | m/s² | Gravity-compensated |
| Gyro Mag | °/s | Combined magnitude |
| Roll | degrees | Complementary filter output |
| Pitch | degrees | Complementary filter output |

### 7.8 PDF Report Export
Clicking **Generate Report** creates a printable HTML report containing:
- Patient name, ID, age, date
- Session duration and sample count
- All UPDRS findings (score, amplitude, frequency, type)
- Embedded chart images (PNG snapshots)
- Clinical notes field

---

## 8. Signal Processing Pipeline

### On-Device (ESP32 Firmware)
```
Raw ADC → MA32 → IIR HP Filter → RMS50 → [JSON Send]
                                                │
IMU Raw → Calibration Offset Subtract → Complementary Filter → Roll/Pitch
```

### On-Dashboard (Browser JavaScript)
```
API JSON → Sort by timestamp → Session filter (t >= sessionStart)
                                        │
                            Gravity Baseline (first 10 samples avg)
                                        │
                    ┌───────────────────┼──────────────────┐
                    │                   │                  │
              Amplitude calc        FFT chain          UPDRS
           (3D Euclidean dist)   (Hann → DFT       (threshold
            after gravity sub)    → EMA smooth)      classifier)
```

### Unit Conversion (LSB → Physical)
The backend stores accel/gyro in raw LSB for backward compatibility.
The dashboard converts in JS:

```javascript
const toAccMs2  = lsb => (lsb / 16384.0) * 9.81;   // → m/s²
const toGyroDps = lsb => lsb / 131.0;               // → degrees/second
```

---

## 9. UPDRS Tremor Classification

The dashboard classifies tremor severity using amplitude and frequency thresholds:

### Amplitude → UPDRS Score
| Amplitude (m/s²) | UPDRS Score | Label |
|-----------------|-------------|-------|
| < 0.05 | 0 | **Absent** |
| 0.05 – 0.35 | 1–2 | **Mild** |
| 0.35 – 0.60 | 3 | **Moderate** |
| ≥ 0.60 | 4 | **Marked** |

### Frequency → Tremor Type
| Dominant Frequency | Type | Clinical Significance |
|--------------------|------|-----------------------|
| < 0.5 Hz | None / Postural sway | Not a tremor |
| 0.5 – 3 Hz | **Rest Tremor** | Classic Parkinson's at rest |
| 3 – 6 Hz | **Rest/Essential** | Overlap zone — needs clinical context |
| 6 – 12 Hz | **Essential Tremor** | Action/postural tremor |
| > 12 Hz | Artifact / noise | Filtered by Hann window |

> ⚠️ **Note:** At the current 5 Hz transmission rate, the Nyquist limit is ~2.5 Hz.
> To reliably detect 3–12 Hz tremors, increase transmission to at least 25 Hz
> (`SEND_INTERVAL_MS = 40` in Config namespace).

---

## 10. Calibration Procedure

### Step 1 — Firmware IMU Calibration (runs automatically on boot)
1. Power on the ESP32
2. **Serial Monitor** will print: `[IMU] Calibrating — hold arm in resting position, keep still...`
3. Hold the patient's arm in the **natural resting clinical position** (not flat on a table)
4. Wait ~2 seconds while 512 samples are averaged
5. The full gravity vector at that orientation is stored as an offset
6. **Confirmation message:** `[IMU] Calibration done. Gravity magnitude: X.XXX m/s² (expect ~9.81)`

> **Critical:** If the magnitude printed is outside 8.5–11.0 m/s², the patient moved during calibration. Power-cycle and repeat.

### Step 2 — Dashboard Gravity Baseline (automatic, first 10 session samples)
After clicking **Start Monitoring**:
1. Dashboard collects the first **10 data frames** (~2 seconds)
2. Computes average X, Y, Z acceleration across those 10 frames
3. Stores as `gBase = {x, y, z}` — the residual gravity vector in the server coordinate frame
4. Sets `gBaseSet = true` — enables amplitude calculation and FFT
5. **All subsequent readings have `gBase` subtracted** before any calculations

> This double-calibration ensures that even if the patient slightly shifts position between power-on and session start, the amplitude readings remain centered at zero.

### Calibration State Flags (Dashboard)
| Flag | Meaning |
|------|---------|
| `gBaseSet = false` | Calibration not done — `ampOf()` returns `0`, FFT skipped |
| `gBaseSet = true` | Calibration complete — all processing enabled |
| `smoothedFreq = 0` | Reset on each new session start |

---

## 11. Project File Structure

```
hardware/
├── biosensor_backend/                  ← Django project root
│   ├── manage.py
│   ├── db.sqlite3                      ← SQLite database (gitignored)
│   ├── simulate_esp32.py               ← Test script to simulate ESP32 data
│   ├── biosensor_backend/
│   │   ├── settings.py                 ← Django settings
│   │   ├── urls.py                     ← Root URL dispatcher
│   │   └── wsgi.py
│   └── biosensor_api/
│       ├── models.py                   ← Patient, SensorReading, TestSession
│       ├── views.py                    ← All view logic (API + HTML)
│       ├── urls.py                     ← URL patterns
│       ├── serializers.py              ← DRF serializers
│       └── templates/
│           ├── login.html              ← Doctor login (centered, dark theme)
│           ├── register.html           ← Doctor signup
│           ├── doctor_dashboard.html   ← Main clinical dashboard (SPA)
│           ├── patient_list.html       ← Patient register
│           ├── patient_form.html       ← Add patient form
│           ├── patient_detail.html     ← Individual patient history
│           ├── settings.html           ← System settings page
│           └── reports_list.html       ← All reports view
│
└── neurosense_firmware/
    └── neurosense_firmware.ino         ← ESP32 Arduino firmware (v2.1)
```

---

## 12. Setup & Running Locally

### Prerequisites
- Python 3.10+
- pip
- Arduino IDE (for firmware flashing)

### Backend Setup
```bash
# 1. Navigate to project
cd hardware/biosensor_backend

# 2. Install dependencies
pip install django djangorestframework

# 3. Apply database migrations
python manage.py migrate

# 4. Create a superuser (optional, for admin panel)
python manage.py createsuperuser

# 5. Start server (accessible from ESP32 on local WiFi)
python manage.py runserver 0.0.0.0:8000
```

### Access Points
| URL | Purpose |
|-----|---------|
| `http://127.0.0.1:8000/` | Login page |
| `http://127.0.0.1:8000/register/` | Create doctor account |
| `http://127.0.0.1:8000/doctor-dashboard/` | Clinical dashboard |
| `http://127.0.0.1:8000/patients/add/` | Register new patient |
| `http://127.0.0.1:8000/admin/` | Django admin panel |

### Test Without ESP32 (Simulator)
```bash
python simulate_esp32.py
```
This script sends synthetic sensor data to the API at regular intervals so you can test the dashboard without hardware.

---

## 13. Connecting Your ESP32

### Firmware Configuration
Open `neurosense_firmware.ino` and update:
```cpp
constexpr char SSID[]         = "YOUR_WIFI_SSID";
constexpr char PASSWORD[]     = "YOUR_WIFI_PASSWORD";
constexpr char API_ENDPOINT[] = "http://YOUR_PC_IP:8000/api/sensor-data/";
```

### Find Your PC's Local IP
```powershell
ipconfig
# Look for "IPv4 Address" under your WiFi adapter
# Example: 172.29.167.126
```

### Required Arduino Libraries
Install via **Arduino IDE → Tools → Manage Libraries**:
- `Adafruit MPU6050`
- `Adafruit Unified Sensor`
- `ArduinoJson` (version 6.x)

### Windows Firewall
You must allow Django through the firewall:
```powershell
# Run as Administrator
netsh advfirewall firewall add rule name="NeuroSense Django" dir=in action=allow protocol=TCP localport=8000
```

### Transmission Rate (Important)
| Setting | Rate | Nyquist Limit | Detectable Tremor |
|---------|------|--------------|-------------------|
| `SEND_INTERVAL_MS = 200` | 5 Hz | 2.5 Hz | Slow movements only |
| `SEND_INTERVAL_MS = 50` | 20 Hz | 10 Hz | Rest tremor (3–6 Hz) ✓ |
| `SEND_INTERVAL_MS = 40` | 25 Hz | 12.5 Hz | Essential tremor (6–12 Hz) ✓ |

> **Recommendation:** Set `SEND_INTERVAL_MS = 50` for reliable clinical tremor detection.

---

## 14. Known Limitations & Future Work

### Current Limitations
| Issue | Cause | Workaround |
|-------|-------|------------|
| FFT capped at 2.5 Hz | 5 Hz transmission rate | Increase to 20+ Hz |
| No patient-session linking | SensorReadings are device-level, not patient-level | Use session start/stop timestamps to filter |
| No login enforcement | `@login_required` not applied to dashboard | Add decorator once auth workflow finalized |
| SQLite in production | Not suitable for concurrent writes | Migrate to PostgreSQL |

### Planned Features
- [ ] Increase ESP32 transmission rate to 20 Hz for clinical-grade FFT
- [ ] Link sensor readings to patient + session IDs at the database level
- [ ] Add `@login_required` to all protected views
- [ ] PostgreSQL migration for production
- [ ] Historical session comparison charts
- [ ] Export session data as CSV for research analysis
- [ ] Mobile-responsive dashboard layout
- [ ] Nurse/technician role with limited access

---

## Technical Contacts

**Repository:** [github.com/Ayush09006/NeuroSense-Hardware](https://github.com/Ayush09006/NeuroSense-Hardware)  
**Stack:** Django 5.0.1 · DRF · SQLite · Chart.js · Bootstrap 5.3.3 · ESP32 Arduino  
**Firmware Version:** v2.1  
**Backend Version:** v2.1  

---

*NeuroSense is a research and clinical-aid tool. It is not a certified medical device.*
