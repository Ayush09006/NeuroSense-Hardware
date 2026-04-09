from django.db import models
from django.contrib.auth.models import User


class Patient(models.Model):
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="patients")
    name = models.CharField(max_length=200)
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, blank=True)
    patient_id = models.CharField(max_length=50, unique=True)  # hospital/clinic ID
    diagnosis = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.patient_id})"


class SensorReading(models.Model):
    # Identification
    device_id  = models.CharField(max_length=64, default="unknown")
    ts_ms      = models.BigIntegerField(default=0)
    timestamp  = models.DateTimeField(auto_now_add=True)

    # EMG — v2 pipeline outputs
    emg_raw      = models.IntegerField(default=0)
    emg_filtered = models.TextField(default="0")      # MA filtered (TextField to tolerate legacy '[0]' values)
    emg_rms      = models.FloatField(default=0.0)     # RMS envelope
    emg_rms_pct  = models.FloatField(default=0.0)     # % of full scale
    emg_voltage  = models.FloatField(default=0.0)

    # IMU — stored as LSB (backward-compatible with JS dashboard)
    acc_x  = models.FloatField(default=0.0)
    acc_y  = models.FloatField(default=0.0)
    acc_z  = models.FloatField(default=0.0)
    gyro_x = models.FloatField(default=0.0)
    gyro_y = models.FloatField(default=0.0)
    gyro_z = models.FloatField(default=0.0)

    # IMU — v2 new fields (physical units)
    roll           = models.FloatField(default=0.0)   # degrees
    pitch          = models.FloatField(default=0.0)   # degrees
    imu_temp       = models.FloatField(default=0.0)   # °C
    imu_calibrated = models.BooleanField(default=False)

    # Connectivity
    wifi_rssi = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.device_id} @ {self.ts_ms}ms | EMG RMS: {self.emg_rms_pct:.1f}%"


class TestSession(models.Model):
    """
    Summary of one 90-sec test window for a patient.
    """
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="tests"
    )
    doctor = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="test_sessions"
    )

    started_at = models.DateTimeField()
    ended_at = models.DateTimeField()

    num_readings = models.IntegerField(default=0)

    avg_emg_voltage = models.FloatField(default=0)
    avg_acc_mag = models.FloatField(default=0)
    avg_gyro_mag = models.FloatField(default=0)

    avg_emg_raw_thumb = models.FloatField(null=True, blank=True)
    avg_emg_raw_index = models.FloatField(null=True, blank=True)
    avg_emg_raw_middle = models.FloatField(null=True, blank=True)
    avg_emg_raw_ring = models.FloatField(null=True, blank=True)
    avg_emg_raw_little = models.FloatField(null=True, blank=True)

    tremor_score = models.FloatField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"TestSession #{self.id} for {self.patient.name}"
