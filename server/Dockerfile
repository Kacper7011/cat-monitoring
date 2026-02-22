FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive
# Wyłączenie buforowania logów Pythona (lepiej widoczne w kontenerze)
ENV PYTHONUNBUFFERED=1 

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Najpierw instalujemy zależności
RUN pip install --no-cache-dir flask flask-cors numpy ultralytics opencv-python-headless

# Kopiujemy TYLKO pliki aplikacji (reszta zostanie odcięta przez .dockerignore)
COPY . .

# Tworzymy puste foldery, aby aplikacja nie miała problemów z zapisem
RUN mkdir -p logs captures

# Model yolov8n.pt już masz w folderze (widać na screenie), 
# więc COPY go przeniosło. Nie musimy go pobierać ponownie skryptem.

EXPOSE 5000

CMD ["python", "app.py"]