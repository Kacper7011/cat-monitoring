document.addEventListener('DOMContentLoaded', () => {
    const statusElement = document.getElementById('last-seen');
    const zoomSlider = document.getElementById('zoom-slider');
    const zoomVal = document.getElementById('zoom-val');
    const torchBtn = document.getElementById('torch-btn');
    const logViewer = document.getElementById('log-viewer');
    const gallery = document.getElementById('gallery');
    
    let isTorchOn = false;

    // Odświeżanie statusu i archiwum
    async function refreshData() {
        try {
            const sRes = await fetch('/status');
            const sData = await sRes.json();
            statusElement.innerText = sData.last_seen;

            const lRes = await fetch('/get_logs');
            logViewer.innerText = await lRes.text();
            logViewer.scrollTop = logViewer.scrollHeight;

            const gRes = await fetch('/get_captures');
            const images = await gRes.json();
            gallery.innerHTML = '';
            images.forEach(name => {
                const img = document.createElement('img');
                img.src = `/captures/${name}`;
                img.onclick = () => window.open(img.src, '_blank');
                gallery.appendChild(img);
            });
        } catch (e) { console.log("Błąd odświeżania danych"); }
    }

    async function updateCamera() {
        await fetch('/settings', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ zoom: zoomSlider.value, flashlight: isTorchOn })
        });
    }

    zoomSlider.addEventListener('input', () => {
        zoomVal.innerText = zoomSlider.value;
        updateCamera();
    });

    torchBtn.addEventListener('click', () => {
        isTorchOn = !isTorchOn;
        torchBtn.innerText = isTorchOn ? "Latarka: ON" : "Latarka: OFF";
        torchBtn.classList.toggle('active', isTorchOn);
        updateCamera();
    });

    setInterval(refreshData, 5000); // Częstsze odświeżanie dla logów
    refreshData();
});