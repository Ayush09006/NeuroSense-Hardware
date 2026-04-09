import ast
from rest_framework import serializers
from .models import SensorReading, TestSession, Patient


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ["id", "name", "age", "gender", "patient_id", "created_at"]


class SensorReadingSerializer(serializers.ModelSerializer):
    """
    One raw biosensor reading used by the doctor dashboard.
    Frontend expects:
      id, timestamp, emg_raw, emg_voltage, acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z

    Note: emg_filtered is coerced to int to handle legacy DB rows
    where it may have been stored as a stringified list e.g. '[0]'.
    """
    emg_filtered = serializers.SerializerMethodField()

    def get_emg_filtered(self, obj):
        val = obj.emg_filtered
        if isinstance(val, int):
            return val
        try:
            return int(val)
        except (TypeError, ValueError):
            pass
        # Handle stringified lists like '[0]' or '[1234]'
        try:
            parsed = ast.literal_eval(str(val))
            if isinstance(parsed, list) and parsed:
                return int(parsed[0])
            return int(parsed)
        except Exception:
            return 0

    class Meta:
        model = SensorReading
        fields = "__all__"


class SensorDataSerializer(SensorReadingSerializer):
    """
    Alias – if any code imports SensorDataSerializer, this keeps it working.
    """
    pass


class TestSessionSerializer(serializers.ModelSerializer):
    patient = PatientSerializer(read_only=True)

    class Meta:
        model = TestSession
        fields = "__all__"
