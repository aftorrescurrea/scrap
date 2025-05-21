FROM python:3.10-slim

# Instalar Firefox y dependencias
RUN apt-get update && apt-get install -y \
    firefox-esr \
    wget \
    unzip \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Descargar e instalar GeckoDriver
RUN wget -q "https://github.com/mozilla/geckodriver/releases/download/v0.34.0/geckodriver-v0.34.0-linux64.tar.gz" \
    && tar -xzf geckodriver-v0.34.0-linux64.tar.gz -C /usr/local/bin \
    && chmod +x /usr/local/bin/geckodriver \
    && rm geckodriver-v0.34.0-linux64.tar.gz

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements.txt y descargar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar script
COPY download_cremil.py .

# Crear directorio para comprobantes
RUN mkdir -p ./comprobantes

# Variables de entorno predeterminadas
ENV ANO_INICIO=2024
ENV MES_INICIO=1
ENV ANO_FIN=2025
ENV MES_FIN=12
ENV DISPLAY=:99

# Comando para ejecutar
CMD Xvfb :99 -screen 0 1920x1080x24 -ac & \
    python download_cremil.py