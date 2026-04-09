from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .models import SensorReading
from .serializers import SensorReadingSerializer

def safe_int(val):
    try:
        if isinstance(val, str) and val.startswith('[') and val.endswith(']'):
            val = val[1:-1]
        return int(float(val))
    except:
        return 0

@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def sensor_data(request):
    try:
        data = request.data
        emg_dict = data.get("emg", {}) or {}
        imu_dict = data.get("imu", {}) or {}

        if not imu_dict or not imu_dict.get("valid", False):
            return Response(
                {"status": "error", "message": "Invalid or missing IMU data"},
                status=status.HTTP_400_BAD_REQUEST
            )

        emg_raw = safe_int(emg_dict.get("raw", 0))
        emg_filtered = safe_int(emg_dict.get("ma_filtered", 0))
        emg_rms = float(emg_dict.get("rms", 0.0))
        emg_rms_pct = float(emg_dict.get("rms_percent", 0.0))
        emg_voltage = float(emg_dict.get("voltage", 0.0))

        accel = imu_dict.get("accel", {}) or {}
        acc_x = (float(accel.get("x", 0.0)) / 9.81) * 16384.0
        acc_y = (float(accel.get("y", 0.0)) / 9.81) * 16384.0
        acc_z = (float(accel.get("z", 0.0)) / 9.81) * 16384.0

        _gyro = imu_dict.get("gyro", {}) or {}
        gyro_x = (float(_gyro.get("x", 0.0)) * 57.2958) * 131.0
        gyro_y = (float(_gyro.get("y", 0.0)) * 57.2958) * 131.0
        gyro_z = (float(_gyro.get("z", 0.0)) * 57.2958) * 131.0

        roll = float(imu_dict.get("roll", 0.0))
        pitch = float(imu_dict.get("pitch", 0.0))
        imu_temp = float(imu_dict.get("temp_c", 0.0))
        imu_calibrated = bool(imu_dict.get("calibrated", False))
        wifi_rssi = safe_int(data.get("wifi_rssi", 0))

        payload = {
            "device_id": str(data.get("device_id", "unknown")),
            "ts_ms": safe_int(data.get("ts_ms", 0)),
            "emg_raw": emg_raw,
            "emg_filtered": emg_filtered,
            "emg_rms": emg_rms,
            "emg_rms_pct": emg_rms_pct,
            "emg_voltage": emg_voltage,
            "acc_x": acc_x,
            "acc_y": acc_y,
            "acc_z": acc_z,
            "gyro_x": gyro_x,
            "gyro_y": gyro_y,
            "gyro_z": gyro_z,
            "roll": roll,
            "pitch": pitch,
            "imu_temp": imu_temp,
            "imu_calibrated": imu_calibrated,
            "wifi_rssi": wifi_rssi,
        }

        serializer = SensorReadingSerializer(data=payload)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "ok"}, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["GET"])
@permission_classes([AllowAny])
def sensor_data_list(request):
    try:
        limit = int(request.GET.get("limit", 200))
    except ValueError:
        limit = 200

    readings = SensorReading.objects.all().order_by("-timestamp")[:limit]
    
    output = []
    for r in readings:
        data = SensorReadingSerializer(r).data
        data["emg_raw"] = safe_int(data.get("emg_raw", 0))
        output.append(data)
    return Response(output)

# --- HTML PAGE VIEWS ---
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Patient, TestSession

def login_view(request):
    if request.method == "POST":
        from django.contrib.auth import authenticate, login
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect("/doctor-dashboard/")
        return render(request, "login.html", {"error": "Invalid credentials"})
    return render(request, "login.html")

def logout_view(request):
    from django.contrib.auth import logout
    logout(request)
    return redirect("/")

def patient_list(request):
    patients = Patient.objects.filter(doctor=request.user).order_by("-created_at") if request.user.is_authenticated else Patient.objects.all().order_by("-created_at")
    return render(request, "patient_list.html", {"patients": patients})

def patient_create(request):
    if request.method == "POST":
        name       = request.POST.get("name", "").strip()
        age        = request.POST.get("age", None)
        gender     = request.POST.get("gender", "")
        patient_id = request.POST.get("patient_id", "").strip()
        diagnosis  = request.POST.get("diagnosis", "")
        notes      = request.POST.get("notes", "")

        if not name or not patient_id:
            return render(request, "patient_form.html", {"error": "Full Name and Patient ID are required."})

        if Patient.objects.filter(patient_id=patient_id).exists():
            return render(request, "patient_form.html", {"error": f"Patient ID '{patient_id}' already exists. Use a unique ID."})

        doctor = request.user if request.user.is_authenticated else None
        # If not logged in (dev mode), use first superuser
        if doctor is None:
            from django.contrib.auth.models import User
            doctor = User.objects.filter(is_superuser=True).first()

        Patient.objects.create(
            doctor=doctor,
            name=name,
            age=int(age) if age and age.isdigit() else None,
            gender=gender,
            patient_id=patient_id,
            diagnosis=diagnosis,
            notes=notes,
        )
        return redirect("/patients/")

    return render(request, "patient_form.html")

def patient_detail(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    sessions = TestSession.objects.filter(patient=patient).order_by("-started_at")
    return render(request, "patient_detail.html", {"patient": patient, "sessions": sessions})

def doctor_dashboard(request):
    return render(request, "doctor_dashboard.html")

def test_session_summary(request, pk):
    session = get_object_or_404(TestSession, pk=pk)
    return render(request, "test_session_summary.html", {"session": session})

def tests_list(request):
    sessions = TestSession.objects.all().order_by("-started_at")
    return render(request, "tests_list.html", {"sessions": sessions})

def reports_list(request):
    patients = Patient.objects.all().order_by("-created_at")
    return render(request, "reports_list.html", {"patients": patients})

def settings_view(request):
    return render(request, "settings.html")

@api_view(["GET"])
def patient_list_api(request):
    patients = Patient.objects.all().order_by("-created_at")
    from .serializers import PatientSerializer
    return Response(PatientSerializer(patients, many=True).data)

@api_view(["GET"])
def patient_detail_api(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    from .serializers import PatientSerializer
    return Response(PatientSerializer(patient).data)

@api_view(["POST"])
def save_test_session(request): return Response({})

