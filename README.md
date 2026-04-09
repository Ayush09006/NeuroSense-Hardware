# ESP32 Biosensor Django Backend

This project contains a production-ready Django REST backend and real-time dashboard designed for ESP32 biomedical sensors tracking EMG and IMU data.

## Project Structure
```
biosensor_backend/
├── biosensor_api/
│   ├── models.py           # Database models (SensorReading, TestSession)
│   ├── serializers.py      # Automated JSON parsers mapped to models
│   ├── views.py            # API routing logic & dashboard loader
│   ├── urls.py             # App route configuration
│   └── templates/
│       └── dashboard.html  # Modern Doctor UI with Tailwind + Chart.js
├── biosensor_backend/
│   ├── settings.py         # Main Django configurations (DRF configured)
│   ├── urls.py             # Root routing
│   └── wsgi.py
├── db.sqlite3              # Central database
├── manage.py
└── simulate_esp32.py       # Python script generating dummy data
```

## Quick Start Setup

Ensure you have Python installed, then install requirements:
```bash
pip install django djangorestframework requests
```

If it's the first time running:
```bash
cd biosensor_backend
python manage.py makemigrations
python manage.py migrate
```

Start the system for local network access:
```bash
python manage.py runserver 0.0.0.0:8000
```
Then, open the dashboard locally: `http://localhost:8000`

## How to Test the Interface (Dummy Sensor)

Open a new terminal while the server is running, and launch the dummy sensor sender:
```bash
python simulate_esp32.py
```
Check your dashboard. The chart should instantly animate with voltage data, and indicators will respond dynamically to spikes.

---

## 🔥 ESP32 IP Configuration Guide 🔥

For your physical hardware (ESP32) to connect properly to this backend:

1. **Find your Computer's Local IP**
   - On Windows, open Command Prompt and type `ipconfig`.
   - Look for "IPv4 Address" (e.g. `192.168.1.52`).

2. **Configure your ESP32 Code**
   In your Arduino / ESP-IDF C++ code, update the destination URL strictly pointing to your computer's IP. The device must be on the same WiFi network!

   ```cpp
   // Change to your laptop's Local IP
   String serverName = "http://192.168.1.52:8000/api/sensor-data/";
   
   // Create HTTP client
   HTTPClient http;
   http.begin(serverName);
   http.addHeader("Content-Type", "application/json");
   ```

3. **Running the Server**
   IMPORTANT: You must run the server with `0.0.0.0:8000` for it to listen on the local network (do not just use `manage.py runserver` which defaults to `127.0.0.1` and blocks external hardware):
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```
