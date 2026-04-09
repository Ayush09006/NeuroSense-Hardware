from django.urls import path
from . import views

urlpatterns = [
    # ---------- HTML PAGES ----------
    path("", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    path("patients/", views.patient_list, name="patient-list"),
    path("patients/add/", views.patient_create, name="patient-create"),
    path("patients/<int:patient_id>/", views.patient_detail, name="patient-detail"),

    path("doctor-dashboard/", views.doctor_dashboard, name="doctor-dashboard"),
    path(
        "api/test-session/<int:pk>/summary/",
        views.test_session_summary,
        name="test-session-summary",
    ),
    
    path("tests/", views.tests_list, name="tests-list"),
    path("reports/", views.reports_list, name="reports-list"),
    path("settings/", views.settings_view, name="settings"),

    # ---------- JSON / API (used by JS + ESP32) ----------
    path("api/patients/", views.patient_list_api, name="patient-list-api"),
    path(
        "api/patients/<int:patient_id>/",
        views.patient_detail_api,
        name="patient-detail-api",
    ),

    path("api/sensor-data/", views.sensor_data, name="sensor-data"),
    path("api/sensor-data", views.sensor_data, name="sensor-data-no-slash"), # Fallback for ESP32 strict URL parsers
    path("api/sensor-data/list/", views.sensor_data_list, name="sensor-data-list"),
    path("api/test-session/save/", views.save_test_session, name="test-session-save"),
]
