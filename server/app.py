import os
import glob
import time
import threading
import queue
import cv2
import numpy as np
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, Response, send_from_directory
from flask_cors import CORS
from ultralytics import YOLO

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# --- KONFIGURACJA AI ---
model = YOLO('yolov8n.pt') 
CAT_CLASS_ID = 15 
COOLDOWN_SECONDS = 5 

# --- KONFIGURACJA ZAPISU I LOGÓW ---
SAVE_COOLDOWN_SECONDS = 1800  # 30 minut
last_save_timestamp = 0
LOG_DIR = "logs"
CAPTURE_DIR = "captures"

for d in [LOG_DIR, CAPTURE_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

# --- FUNKCJA CZASU (Poprawka o +1h) ---
def get_now():
    # Jeśli nadal masz godzinę do tyłu, zwiększ hours=1. Jeśli serwer ma OK, ustaw 0.
    return datetime.now() + timedelta(hours=1)

# --- KONFIGURACJA WYGŁADZANIA ---
ALPHA = 0.3 
smoothed_box = None 

# --- ZMIENNE GLOBALNE ---
latest_frame = None
last_cat_seen = "Nigdy"
last_detection_timestamp = 0
ai_queue = queue.Queue(maxsize=1)
new_frame_event = threading.Event()

camera_settings = {
    "zoom": 1.0,
    "flashlight": False
}

def log(message):
    print(f"[{get_now().strftime('%H:%M:%S')}] {message}", flush=True)

def save_cat_event(img):
    global last_save_timestamp
    current_time = time.time()
    
    if current_time - last_save_timestamp > SAVE_COOLDOWN_SECONDS:
        last_save_timestamp = current_time
        now = get_now()
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        
        photo_name = f"cat_{timestamp_str}.jpg"
        photo_path = os.path.join(CAPTURE_DIR, photo_name)
        cv2.imwrite(photo_path, img)
        
        log_path = os.path.join(LOG_DIR, "cat_activity.txt")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Wykryto kota! Foto: {photo_name}\n")
        
        log(f"📸 ZDARZENIE ZAPISANE: {photo_path}")

def ai_worker():
    global last_cat_seen, last_detection_timestamp, latest_frame, smoothed_box
    log("Wątek AI uruchomiony.")
    
    while True:
        frame_bytes = ai_queue.get()
        try:
            nparr = np.frombuffer(frame_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img is not None:
                raw_img = img.copy()
                results = model.predict(img, classes=[CAT_CLASS_ID], conf=0.3, verbose=False)
                best_box = None
                max_conf = 0

                for result in results:
                    for box in result.boxes:
                        conf = float(box.conf[0])
                        if conf > max_conf:
                            max_conf = conf
                            best_box = list(map(int, box.xyxy[0]))

                if best_box:
                    x1, y1, x2, y2 = best_box
                    if smoothed_box is None:
                        smoothed_box = [x1, y1, x2, y2]
                    else:
                        smoothed_box[0] = int(smoothed_box[0] * (1 - ALPHA) + x1 * ALPHA)
                        smoothed_box[1] = int(smoothed_box[1] * (1 - ALPHA) + y1 * ALPHA)
                        smoothed_box[2] = int(smoothed_box[2] * (1 - ALPHA) + x2 * ALPHA)
                        smoothed_box[3] = int(smoothed_box[3] * (1 - ALPHA) + y2 * ALPHA)

                    bx1, by1, bx2, by2 = smoothed_box
                    cv2.rectangle(img, (bx1, by1), (bx2, by2), (0, 255, 0), 2)
                    cv2.putText(img, f"KOT {max_conf:.2f}", (bx1, by1 - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                    save_cat_event(raw_img)

                    _, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 50])
                    latest_frame = buffer.tobytes()
                    new_frame_event.set()

                    current_time = time.time()
                    if current_time - last_detection_timestamp > COOLDOWN_SECONDS:
                        last_detection_timestamp = current_time
                        last_cat_seen = get_now().strftime("%H:%M:%S")
                        log("🔥 KOT WIDOCZNY")
                else:
                    smoothed_box = None
        except Exception as e:
            log(f"Błąd AI: {e}")
        ai_queue.task_done()

threading.Thread(target=ai_worker, daemon=True).start()

# --- ENDPOINTY ---

@app.route('/')
def index():
    return render_template('index.html', last_seen=last_cat_seen)

@app.route('/status')
def get_status():
    return jsonify({"last_seen": last_cat_seen})

@app.route('/settings', methods=['GET', 'POST'])
def handle_settings():
    global camera_settings
    if request.method == 'POST':
        data = request.json
        # Ograniczenie zoomu do 3.0
        new_zoom = float(data.get("zoom", camera_settings["zoom"]))
        camera_settings["zoom"] = max(1.0, min(3.0, new_zoom))
        camera_settings["flashlight"] = bool(data.get("flashlight", camera_settings["flashlight"]))
        return jsonify({"status": "ok"})
    return jsonify(camera_settings)

@app.route('/get_logs')
def get_logs():
    path = os.path.join(LOG_DIR, "cat_activity.txt")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return "Brak aktywności w logach."

@app.route('/get_captures')
def get_captures():
    files = glob.glob(os.path.join(CAPTURE_DIR, "*.jpg"))
    files.sort(key=os.path.getmtime, reverse=True)
    return jsonify([os.path.basename(f) for f in files[:12]])

@app.route('/captures/<filename>')
def serve_capture(filename):
    return send_from_directory(CAPTURE_DIR, filename)

@app.route('/upload_frame', methods=['POST'])
def upload_frame():
    global latest_frame
    if not request.data: return "No Data", 400
    latest_frame = request.data
    new_frame_event.set()
    try:
        ai_queue.put_nowait(request.data)
    except queue.Full: pass 
    return "OK", 200

@app.route('/video_feed')
def video_feed():
    def generate():
        while True:
            if new_frame_event.wait(timeout=1.0):
                new_frame_event.clear()
                if latest_frame:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + latest_frame + b'\r\n')
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)