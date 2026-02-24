document.addEventListener('DOMContentLoaded', () => {
    const statusElement = document.getElementById('last-seen');
    const batteryBar = document.getElementById('battery-level-bar');
    const batteryText = document.getElementById('battery-text');
    const zoomSlider = document.getElementById('zoom-slider');
    const zoomVal = document.getElementById('zoom-val');
    const torchBtn = document.getElementById('torch-btn');
    const logViewer = document.getElementById('log-viewer');
    const gallery = document.getElementById('gallery');
    const streamImg = document.getElementById('main-stream');

    let isTorchOn = false;

    /**
     * Aktualizuje graficzny interfejs baterii (pasek + tekst + kolor)
     */
    function updateBatteryUI(batteryStr) {
        if (!batteryBar || !batteryText || !batteryStr) return;
        
        const level = parseInt(batteryStr);
        batteryText.innerText = batteryStr;

        if (isNaN(level)) {
            batteryBar.style.width = "0%";
            return;
        }

        // Ustawienie szerokości paska (wykorzystuje transition z CSS dla płynności)
        batteryBar.style.width = level + "%";

        // Dynamiczna zmiana kolorów zależnie od poziomu naładowania
        let color = "#ff4444"; // Czerwony (domyślny dla niskiego stanu)
        if (level > 60) {
            color = "#44ff44"; // Zielony
        } else if (level > 20) {
            color = "#ffdd44"; // Żółty
        }

        batteryBar.style.backgroundColor = color;
        batteryText.style.color = color;
    }

    /**
     * Pobiera dane z serwera i aktualizuje UI
     */
    async function refreshData() {
        try {
            // 1. Pobieranie statusu (ostatnie widzenie + bateria)
            const sRes = await fetch('/status?t=' + Date.now(), { cache: "no-store" });
            if (sRes.ok) {
                const sData = await sRes.json();
                
                if (sData.last_seen && sData.last_seen !== "Nigdy" && sData.last_seen !== "") {
                    statusElement.innerText = sData.last_seen;
                } else {
                    statusElement.innerText = "Brak danych";
                }

                if (sData.battery) {
                    updateBatteryUI(sData.battery);
                }
            }

            // 2. Pobieranie logów
            const lRes = await fetch('/get_logs?t=' + Date.now(), { cache: "no-store" });
            if (lRes.ok) {
                const logText = await lRes.text();
                logViewer.innerText = logText;
                logViewer.scrollTop = logViewer.scrollHeight;
            }

            // 3. Aktualizacja galerii
            const gRes = await fetch('/get_captures?t=' + Date.now(), { cache: "no-store" });
            if (gRes.ok) {
                const images = await gRes.json();
                gallery.innerHTML = '';
                images.forEach(name => {
                    const img = document.createElement('img');
                    img.src = `/captures/${name}?t=${Date.now()}`; 
                    img.onclick = () => window.open(img.src, '_blank');
                    gallery.appendChild(img);
                });
            }
        } catch (e) {
            console.warn("Serwer nie odpowiedział na czas (prawdopodobnie obciążony detekcją).");
        }
    }

    /**
     * Wysyła aktualne parametry kamery do serwera
     */
    async function updateCamera() {
        try {
            await fetch('/settings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ 
                    zoom: parseFloat(zoomSlider.value), 
                    flashlight: isTorchOn 
                })
            });
        } catch (e) {
            console.error("Błąd połączenia przy aktualizacji ustawień.");
        }
    }

    // --- EVENT LISTENERS ---

    zoomSlider.addEventListener('input', () => {
        zoomVal.innerText = parseFloat(zoomSlider.value).toFixed(1);
        updateCamera();
    });

    torchBtn.addEventListener('click', () => {
        isTorchOn = !isTorchOn;
        torchBtn.innerText = isTorchOn ? "Latarka: ON" : "Latarka: OFF";
        torchBtn.classList.toggle('active', isTorchOn);
        updateCamera();
    });

    // Automatyczne odświeżanie co 5 sekund
    setInterval(refreshData, 5000); 
    
    // Inicjalizacja przy starcie
    refreshData();
});