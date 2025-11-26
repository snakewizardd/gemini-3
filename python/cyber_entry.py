import cv2
import numpy as np
import sounddevice as sd
from ultralytics import YOLO
import time
import math
import random
import sys

# ==============================================================================
# CONFIGURATION // HARDWARE OPTIMIZATION
# ==============================================================================
# "Big Buck Bunny" is the only reliable 24/7 public test RTSP stream.
# If this lags, replace with '0' to use your webcam.
RTSP_URL = "rtsp://youtube.com/add_favorite?v=y8cQhHxEL84" 

CONF_THRESHOLD = 0.5
MODEL_TYPE = 'yolov8n.pt'  # Nano model: Best for Snapdragon/CPU
AUDIO_SAMPLE_RATE = 44100
HUD_COLOR = (0, 255, 255)  # Neon Cyan
THREAT_COLOR = (0, 0, 255) # Red

# ==============================================================================
# AUDITORY CORTEX // PROCEDURAL AUDIO ENGINE
# ==============================================================================
class CyberSynth:
    def __init__(self):
        self.phase = 0
        self.threat_level = 0.0 # 0.0 to 1.0
        self.object_count = 0
        self.base_freq = 55.0   # A1 (Deep Bass)
        self.volume = 0.3
        self.is_running = True
        self.stream = sd.OutputStream(
            channels=1, 
            callback=self.audio_callback, 
            samplerate=AUDIO_SAMPLE_RATE
        )
        self.stream.start()

    def update_state(self, threat_level, count):
        # Smooth transition for audio parameters
        self.threat_level = self.threat_level * 0.9 + threat_level * 0.1
        self.object_count = count

    def get_wave(self, t):
        # 1. THE DRONE (Sawtooth)
        # Pitch shifts up slightly with threat
        freq = self.base_freq + (self.threat_level * 100)
        osc1 = 2.0 * (t * freq - np.floor(t * freq + 0.5))
        
        # 2. THE LFO (Low Frequency Oscillator for the "Wub Wub")
        # Speed of wobble increases with object count
        lfo_speed = 2.0 + (self.object_count * 2.0)
        lfo = 0.5 * (1.0 + np.sin(2 * np.pi * lfo_speed * t))
        
        # 3. THE ALARM (High Sine) - Only audible at high threat
        alarm_freq = 880.0 # A5
        if self.threat_level > 0.5:
            # Glitchy frequency modulation
            alarm_freq += np.sin(2 * np.pi * 15 * t) * 100
            
        alarm = np.sin(2 * np.pi * alarm_freq * t) * (self.threat_level * 0.5)

        # Mix: Drone gets filtered by LFO + Alarm added on top
        signal = (osc1 * lfo * 0.6) + alarm
        
        return signal * self.volume

    def audio_callback(self, outdata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
            
        # Generate time array for this buffer chunk
        t = (self.phase + np.arange(frames)) / AUDIO_SAMPLE_RATE
        t = t.reshape(-1, 1)
        
        # Generate audio
        audio = self.get_wave(t)
        
        # Hard Clip Distortion (for that dirty cyberpunk feel)
        audio = np.clip(audio, -0.8, 0.8)
        
        outdata[:] = audio
        self.phase += frames

# ==============================================================================
# VISUAL CORTEX // YOLO & HUD
# ==============================================================================
def draw_hud(frame, boxes, synth):
    height, width, _ = frame.shape
    
    # 1. Cyber Overlay Grid
    cv2.line(frame, (0, height//2), (width, height//2), (0, 255, 0, 50), 1)
    cv2.line(frame, (width//2, 0), (width//2, height), (0, 255, 0, 50), 1)
    
    # 2. Process Detections
    current_threat = 0.0
    detected_objects = len(boxes)
    
    for box in boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cls = int(box.cls[0])
        conf = float(box.conf[0])
        label_name = model.names[cls]

        # DECISION ENGINE: Determine Threat
        # Person = High Threat, Car/Cell phone = Low Threat
        box_color = HUD_COLOR
        if label_name == 'person':
            current_threat = 1.0
            box_color = THREAT_COLOR
        elif current_threat < 0.5:
            current_threat = 0.2

        # Draw "Bracket" style corners (Sick aesthetic)
        l = 20 # Line length
        t = 2  # Thickness
        # Top-Left
        cv2.line(frame, (x1, y1), (x1 + l, y1), box_color, t)
        cv2.line(frame, (x1, y1), (x1, y1 + l), box_color, t)
        # Bottom-Right
        cv2.line(frame, (x2, y2), (x2 - l, y2), box_color, t)
        cv2.line(frame, (x2, y2), (x2, y2 - l), box_color, t)

        # Glitch Text
        label = f"{label_name.upper()} [{conf:.2f}]"
        cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 1)

    # 3. Update Audio Engine
    synth.update_state(current_threat, detected_objects)

    # 4. HUD Status Bar
    bar_width = int(width * 0.3)
    # Background
    cv2.rectangle(frame, (20, height - 40), (20 + bar_width, height - 20), (0, 50, 0), -1)
    # Threat Level Meter
    fill_width = int(bar_width * synth.threat_level)
    meter_color = (0, 255, 255) if synth.threat_level < 0.5 else (0, 0, 255)
    cv2.rectangle(frame, (20, height - 40), (20 + fill_width, height - 20), meter_color, -1)
    
    cv2.putText(frame, f"NEURAL_SYNC: {detected_objects} TARGETS", (20, height - 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 255, 200), 2)

    return frame

# ==============================================================================
# MAIN LOOP // BOOT SEQUENCE
# ==============================================================================
print(">> SYSTEM INITIALIZING...")
print(f">> LOAD_MODEL: {MODEL_TYPE}")
# Load YOLOv8 Nano (optimized for CPU/Mobile)
model = YOLO(MODEL_TYPE) 

print(">> INIT_AUDIO_SYNTHESIS...")
synth = CyberSynth()

print(f">> CONNECT_RTSP: {RTSP_URL}")
cap = cv2.VideoCapture(RTSP_URL)

# Buffer trick for RTSP latency
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

if not cap.isOpened():
    print("!! RTSP CONNECTION FAILED. FALLING BACK TO WEBCAM (0) !!")
    cap = cv2.VideoCapture(0)

frame_count = 0
start_time = time.time()

try:
    while True:
        success, frame = cap.read()
        if not success:
            # Handle RTSP stream end/loop
            print(">> STREAM LOST. RECONNECTING...")
            cap.set(cv2.CAP_PROP_POS_MSEC, 0)
            continue

        # Optimization: Resize for Snapdragon inference speed
        # 640x360 is a sweet spot for detection vs speed
        frame_resized = cv2.resize(frame, (640, 360))

        # INFERENCE
        results = model(frame_resized, stream=True, verbose=False)

        # Extract boxes
        boxes = []
        for r in results:
            boxes = r.boxes

        # RENDER
        frame_hud = draw_hud(frame_resized, boxes, synth)

        # Scale up slightly for display if needed
        display_frame = cv2.resize(frame_hud, (1280, 720))
        
        cv2.imshow('CYBER_SENTRY // RTSP', display_frame)

        # Exit on 'Q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        frame_count += 1

except KeyboardInterrupt:
    pass

# Cleanup
synth.stream.stop()
synth.stream.close()
cap.release()
cv2.destroyAllWindows()
print(">> SYSTEM SHUTDOWN.")