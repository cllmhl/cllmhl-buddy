# Usa un'immagine Python ufficiale
FROM mcr.microsoft.com/devcontainers/python:3.11

# Installa dipendenze di sistema per audio e database (utili per il memory recall)
RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    python3-pyaudio \
    libasound2-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# [LOG] Dockerfile configurato per audio e gestione memoria vettoriale.