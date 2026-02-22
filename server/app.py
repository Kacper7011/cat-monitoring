from flask import Flask, render_template, request, jsonify
import time
from datetime import datetime

app = Flask(__name__)

# --- KONFIGURACJA LOGIKI POWIADOMIEŃ ---
last_detection_time = 0
COOLDOWN_SECONDS = 3600  # 1 godzina przerwy między powiadomieniami

def send_real_notification(msg):
    # Tutaj w przyszłości dodamy np. bota Telegram lub Pushbullet
    print(f"[{datetime.now()}] WYSYŁAM POWIADOMIENIE: {msg}")

@app.route('/')
def index():
    return "Serwer CatWatch AI działa. Czekam na stream..."

@app.route('/detect', methods=['POST'])
def detect_event():
    global last_detection_time
    
    data = request.json
    object_type = data.get('object') # Aplikacja wyśle 'cat'
    
    if object_type == 'cat':
        current_time = time.time()
        time_since_last = current_time - last_detection_time
        
        if time_since_last > COOLDOWN_SECONDS:
            send_real_notification("Wykryto kota po dłuższej przerwie!")
            last_detection_time = current_time
            return jsonify({"status": "notified"}), 200
        else:
            return jsonify({"status": "cooldown", "remaining": COOLDOWN_SECONDS - time_since_last}), 200

    return jsonify({"status": "ignored"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)