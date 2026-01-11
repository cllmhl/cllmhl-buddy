#!/bin/bash

# Uscire immediatamente in caso di errore
set -e

echo "--- 1. Aggiornamento Sistema Operativo ---"
sudo apt-get update
sudo apt-get upgrade -y

echo "--- 2. Installazione dipendenze di sistema (Audio e Sviluppo) ---"
sudo apt-get install -y \
    git \
    portaudio19-dev \
    mpg123 \
    flac \
    alsa-utils \
    libasound2-dev \
    liblgpio-dev \
    swig \
    python3-pip \
    python3-venv \
    python3-dev \
    python3-pyaudio \
    build-essential \
    wget

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
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "Attenzione: requirements.txt non trovato, salto installazione pip."
fi

echo "--- 5. Verifica Dispositivi Audio (Jabra) ---"
echo "Ecco la lista dei dispositivi di registrazione rilevati:"
arecord -l || echo "Nessun dispositivo di registrazione trovato."

echo "--- 6. Installazione Piper TTS (Fuori dal progetto) ---"
# Definiamo la cartella esterna
PIPER_DEST="$HOME/buddy_tools/piper"
mkdir -p "$PIPER_DEST"
cd "$PIPER_DEST"

# Scarica Piper se non esiste già
if [ ! -f "piper/piper" ]; then
    echo "Scaricamento binari Piper..."
    # Versione per Raspberry Pi (aarch64). Cambiare in amd64 se su PC.
    wget https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_aarch64.tar.gz || exit 1
    tar -xvf piper_linux_aarch64.tar.gz
    rm piper_linux_aarch64.tar.gz
else
    echo "Binari Piper già presenti."
fi

# Scarica il modello Riccardo se non esiste già
if [ ! -f "it_IT-riccardo-medium.onnx" ]; then
    echo "Scaricamento modello vocale Riccardo..."
    # URL corretti: cambiato 'v1.0.0' in 'main' e aggiunto exit in caso di errore
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/it/it_IT/riccardo/medium/it_IT-riccardo-medium.onnx || exit 1
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/it/it_IT/riccardo/medium/it_IT-riccardo-medium.onnx.json || exit 1
else
    echo "Modello Riccardo già presente."
fi

echo ""
echo "--- SETUP COMPLETATO ---"
echo "Piper installato in: $PIPER_DEST"
echo "Per avviare Buddy: source venv/bin/activate && python main.py"