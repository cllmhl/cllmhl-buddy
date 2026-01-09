#!/bin/bash

# Uscire immediatamente in caso di errore
set -e

echo "--- 1. Aggiornamento Sistema Operativo ---"
sudo apt-get update
sudo apt-get upgrade -y

echo "--- 2. Installazione dipendenze di sistema (Audio e Sviluppo) ---"
# portaudio19-dev e python3-pyaudio: necessari per registrare dal Jabra
# mpg123: il player leggero che usiamo nel main.py per l'output
# flac: necessario per alcune funzioni di SpeechRecognition
sudo apt-get install -y \
    git \
    portaudio19-dev \
    mpg123 \
    flac \
    libasound2-dev \
    python3-pip \
    python3-venv \
    python3-dev \
    python3-pyaudio \
    build-essential

echo "--- 3. Gestione Ambiente Virtuale Python ---"
if [ ! -d "venv" ]; then
    echo "Creazione ambiente virtuale..."
    python3 -m venv venv
else
    echo "Ambiente virtuale già esistente."
fi

# Attivazione venv
source venv/bin/activate

echo "--- 4. Installazione pacchetti Python da requirements.txt ---"
# Aggiorniamo prima pip e setuptools per evitare problemi con pacchetti binari
pip install --upgrade pip setuptools wheel

# Installazione dei requisiti
pip install -r requirements.txt

echo "--- 5. Verifica Dispositivi Audio (Jabra) ---"
echo "Ecco la lista dei dispositivi di registrazione rilevati:"
arecord -l

echo ""
echo "--- SETUP COMPLETATO ---"
echo "Per avviare Buddy, ricorda di attivare il venv con: source venv/bin/activate"
echo "Poi lancia: python main.py"
