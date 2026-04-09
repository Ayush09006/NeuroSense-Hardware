import os

# Paths
SRC_DIR = "C:/Users/Lenovo/OneDrive/Desktop/hardware/park_backend/glove/"
DST_DIR = "C:/Users/Lenovo/OneDrive/Desktop/hardware/biosensor_backend/biosensor_api/"

def replace_terms(text):
    # Core naming
    text = text.replace("glove_data", "sensor_data")
    text = text.replace("glove-data", "sensor-data")
    text = text.replace("GloveReading", "SensorReading")
    text = text.replace("GloveData", "SensorData")
    text = text.replace("Glove", "Biosensor")
    text = text.replace("glove", "biosensor")
    
    # Specific fields in python/html
    text = text.replace("fsr", "emg_voltage")
    text = text.replace("FSR", "EMG")
    text = text.replace("flex", "emg_raw")
    text = text.replace("Flex", "EMG")
    
    # In test summaries
    text = text.replace("avg_flex_thumb", "peak_emg")
    text = text.replace("avg_flex_index", "avg_emg")
    text = text.replace("avg_flex_middle", "emg_stability")
    text = text.replace("avg_flex_ring", "unused_1")
    text = text.replace("avg_flex_little", "unused_2")

    # New UI Labels
    text = text.replace("Finger Movement", "EMG Channels")
    text = text.replace("finger-", "channel-")
    text = text.replace("Grip Strength", "EMG Amplitude")
    text = text.replace(">Thumb<", ">Channel 1<")
    text = text.replace(">Index<", ">Channel 2<")
    text = text.replace(">Middle<", ">Channel 3<")
    text = text.replace(">Ring<", ">Channel 4<")
    text = text.replace(">Little<", ">Channel 5<")
    text = text.replace("Thumb:", "Ch 1:")
    text = text.replace("Index:", "Ch 2:")
    text = text.replace("Middle:", "Ch 3:")
    text = text.replace("Ring:", "Ch 4:")
    text = text.replace("Little:", "Ch 5:")
    
    return text

def process_file(src_path, dst_path):
    with open(src_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = replace_terms(content)
    
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    with open(dst_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Copied & Transformed: {dst_path}")

# 1. Copy Python logic files
for f in ["models.py", "views.py", "urls.py", "serializers.py"]:
    process_file(os.path.join(SRC_DIR, f), os.path.join(DST_DIR, f))

# 2. Copy Templates
src_templates = os.path.join(SRC_DIR, "templates")
dst_templates = os.path.join(DST_DIR, "templates")

for root, _, files in os.walk(src_templates):
    for f in files:
        if f.endswith(".html"):
            src_path = os.path.join(root, f)
            dst_path = os.path.join(dst_templates, f)
            process_file(src_path, dst_path)

print("Transformation complete!")
