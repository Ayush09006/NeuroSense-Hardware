import requests
import time
import random

URL = "http://127.0.0.1:8000/api/sensor-data/"

print("Starting ESP32 Biosensor dummy sender...")
print(f"Target URL: {URL}")

while True:
    # Scale from 0 to 4095 for EMG voltage (0-100% relative)
    if random.random() > 0.85:
        emg_v = random.randint(2457, 4095) # Spike (60-100%)
    else:
        emg_v = random.randint(409, 1228) # Normal (10-30%)

    # Simulate GYRO
    if random.random() > 0.90:
        gx, gy, gz = random.uniform(-200, 200), random.uniform(-200, 200), random.uniform(-200, 200)
    else:
        gx, gy, gz = random.uniform(-10, 10), random.uniform(-10, 10), random.uniform(-10, 10)

    # 1 G = 16384
    payload = {
        "emg_raw": [],
        "emg_voltage": emg_v,
        "acc": {"x": 5898, "y": 14417, "z": 16072},
        "gyro": {"x": gx, "y": gy, "z": gz}
    }

    try:
        resp = requests.post(URL, json=payload)
    except Exception as e:
        pass

    time.sleep(0.1)
