from flask import Flask, render_template, request, jsonify, Response # Added Response
import time
from datetime import datetime
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Global variable to store the latest frame from the phone
latest_frame = None

# --- NOTIFICATION LOGIC ---
last_detection_time = 0
COOLDOWN_SECONDS = 3600 

@app.route('/')
def index():
    # Renders the HTML page we just created
    return render_template('index.html')

@app.route('/upload_frame', methods=['POST'])
def upload_frame():
    """Endpoint for the Android app to send JPEG frames"""
    global latest_frame
    latest_frame = request.data # The raw binary JPEG data
    return "OK", 200

def generate_frames():
    """Generator that yields the latest frame to the browser"""
    global latest_frame
    while True:
        if latest_frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + latest_frame + b'\r\n')
        time.sleep(0.1) # Limits the refresh rate to ~10 FPS to save CPU

@app.route('/video_feed')
def video_feed():
    """Route that the <img> tag in HTML points to"""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/detect', methods=['POST'])
def detect_event():
    # ... keep your existing detect_event logic here ...
    global last_detection_time
    data = request.json
    if data and data.get('object') == 'cat':
        # (cooldown logic remains the same)
        print(f"[{datetime.now()}] Cat detection received from phone")
        return jsonify({"status": "received"}), 200
    return jsonify({"status": "ignored"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)