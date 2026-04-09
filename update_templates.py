import re
import os

TEMPLATES_DIR = "C:/Users/Lenovo/OneDrive/Desktop/hardware/biosensor_backend/biosensor_api/templates"

def update_doctor_dashboard():
    path = os.path.join(TEMPLATES_DIR, "doctor_dashboard.html")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find where <div class="dashboard-container"> starts
    match = re.search(r'<div class="dashboard-container">\s*', content)
    if not match:
        print("Could not find dashboard-container in doctor_dashboard.html")
        return
        
    start_idx = match.end()
    
    # Everything before <div class="dashboard-container"> gets replaced
    new_header = """{% extends "base_dashboard.html" %}

{% block page_title %}Doctor Dashboard{% endblock %}

{% block topbar_actions %}
<select id="patient-select" class="form-select form-select-sm" style="width: auto;">
    <option value="">-- Select Patient to Save Test --</option>
    {% for p in patients %}
        <option value="{{ p.id }}" {% if p.id|stringformat:"s" == patient_id|stringformat:"s" %}selected{% endif %}>
            {{ p.name }} ({{ p.patient_id }})
        </option>
    {% endfor %}
</select>
<a href="/patients/" class="btn btn-primary d-none d-md-block">Patients</a>
{% endblock %}

{% block extra_css %}
<style>
    /* Control Row */
    .control-row {
        display: flex;
        align-items: center;
        gap: 2rem;
        padding: 1rem 1.5rem;
        background: var(--card-bg);
        border-radius: 12px;
        border: 1px solid var(--border-color);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 1rem;
    }

    .btn-start-large {
        background-color: var(--metric-green);
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        font-size: 1.1rem;
        font-weight: 600;
        border-radius: 8px;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        transition: background 0.2s;
    }

    .btn-start-large:hover { background-color: #15803d; color: white;}
    .btn-start-large:disabled { background-color: var(--text-muted); cursor: not-allowed;}

    .timer-display {
        font-size: 2.5rem;
        font-weight: 700;
        color: var(--text-dark);
        line-height: 1;
    }

    .timer-subtext {
        color: var(--text-muted);
        font-size: 1.1rem;
        font-weight: 500;
        margin-left: auto;
    }

    /* Metrics */
    .metric-title {
        color: var(--text-dark);
        font-size: 0.95rem;
        font-weight: 600;
        text-align: center;
        margin-bottom: 0.5rem;
    }

    .metric-value-large {
        font-size: 2.5rem;
        font-weight: 700;
        text-align: center;
        line-height: 1.1;
    }

    .metric-blue { color: var(--metric-blue); }
    .metric-green { color: var(--metric-green); }
    .metric-red { color: var(--metric-red); }

    .chart-container {
        position: relative;
        height: 220px;
        width: 100%;
    }

    /* insight badges */
    .insight-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 999px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .badge-normal { background: #dcfce7; color: #166534; }
    .badge-none { background: #f1f5f9; color: #475569; }
    .badge-warn { background: #fef08a; color: #854d0e; }
    .badge-danger { background: #fee2e2; color: #991b1b; }

    .btn-report {
        background-color: #3b82f6;
        color: white;
        border: none;
        width: 100%;
        padding: 0.75rem;
        border-radius: 8px;
        font-weight: 600;
        margin-top: 1rem;
    }
</style>
{% endblock %}

{% block content %}
"""
    
    body_content = content[start_idx:]
    # Replace closing tags
    body_content = re.sub(r'</div>\s*</main>\s*<script src="[^"]*"></script>\s*', '{% endblock %}\n\n{% block extra_js %}\n', body_content)
    body_content = re.sub(r'</body>\s*</html>', '\n{% endblock %}\n', body_content)
    
    # write to file
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_header + body_content)
        
    print("doctor_dashboard.html updated.")

def update_patient_list():
    path = os.path.join(TEMPLATES_DIR, "patient_list.html")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    match = re.search(r'<div class="container py-4.*?">\s*(<div class="page-wrapper w-100">\s*)?', content)
    if not match:
        print("patient_list.html match failed")
        return
    start_idx = match.end()

    new_header = """{% extends "base_dashboard.html" %}
{% block title %}NeuroSense - Patients{% endblock %}
{% block page_title %}Patient Directory{% endblock %}

{% block content %}
"""
    
    body_content = content[start_idx:]
    body_content = re.sub(r'</div>\s*</div>\s*(<!--.*?-->\s*)?<script>', '{% endblock %}\n\n{% block extra_js %}\n<script>', body_content)
    body_content = re.sub(r'</body>\s*</html>', '\n{% endblock %}\n', body_content)
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_header + body_content)
        
    print("patient_list.html updated.")

def update_login():
    path = os.path.join(TEMPLATES_DIR, "login.html")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    content = content.replace("Doctor Panel", "NeuroSense Login")
    content = content.replace("PD Biosensor", "NeuroSense Platform")
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("login.html updated.")
    
try:
    update_doctor_dashboard()
    update_patient_list()
    update_login()
except Exception as e:
    print(f"Error: {e}")
