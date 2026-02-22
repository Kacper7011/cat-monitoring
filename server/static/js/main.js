document.addEventListener('DOMContentLoaded', () => {
    const statusElement = document.getElementById('last-seen');
    const zoomSlider = document.getElementById('zoom-slider');
    const zoomVal = document.getElementById('zoom-val');
    const torchBtn = document.getElementById('torch-btn');
    const logViewer = document.getElementById('log-viewer');
    const gallery = document.getElementById('gallery');
    const streamImg = document.getElementById('main-stream');

    let isTorchOn = false;

    // Główna funkcja pobierająca dane (status, logi, galeria)
    async function refreshData() {
        try {
            // Pobieranie statusu
            const sRes = await fetch('/status?t=' + Date.now(), { cache: "no-store" });
            if (sRes.ok) {
                const sData = await sRes.json();
                if (sData.last_seen && sData.last_seen !== "Nigdy" && sData.last_seen !== "") {
                    statusElement.innerText = sData.last_seen;
                } else {
                    statusElement.innerText = "Brak danych";
                }
            }

            // Pobieranie logów systemowych
            const lRes = await fetch('/get_logs?t=' + Date.now(), { cache: "no-store" });
            if (lRes.ok) {
                const logText = await lRes.text();
                logViewer.innerText = logText;
                logViewer.scrollTop = logViewer.scrollHeight;
            }

            // Pobieranie galerii zdjęć
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
            console.warn("Błąd podczas odświeżania danych (serwer może być zajęty).");
        }
    }

    // Funkcja wysyłająca ustawienia (zoom, latarka)
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
            console.error("Błąd: Nie można wysłać ustawień.");
        }
    }

    // Obsługa suwaka Zoom
    zoomSlider.addEventListener('input', () => {
        zoomVal.innerText = parseFloat(zoomSlider.value).toFixed(1);
        updateCamera();
    });

    // Obsługa przycisku Latarki
    torchBtn.addEventListener('click', () => {
        isTorchOn = !isTorchOn;
        torchBtn.innerText = isTorchOn ? "Latarka: ON" : "Latarka: OFF";
        torchBtn.classList.toggle('active', isTorchOn);
        updateCamera();
    });

    // Interwał odświeżania - co 5 sekund pobieramy nowe dane
    setInterval(refreshData, 5000); 
    
    // Pierwsze wywołanie przy załadowaniu strony
    refreshData();
});