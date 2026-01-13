#!/bin/bash

# Uscire immediatamente in caso di errore
set -e

# Ottieni la directory del progetto (parent della cartella scripts)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "🤖 Setup Buddy - Directory Progetto: $PROJECT_DIR"
echo ""

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
    wget \
    sox \
    libsox-fmt-all

echo "--- 3. Gestione Ambiente Virtuale Python ---"
# Controlla sia Dev Containers (REMOTE_CONTAINERS) che Codespaces (CODESPACES)
if [ -n "$REMOTE_CONTAINERS" ] || [ -n "$CODESPACES" ]; then
    echo "Ambiente containerizzato rilevato. Salto la gestione di venv e requirements.txt."
    echo "(Sono gestiti da devcontainer.json o Codespaces)"
else
    # Esegui solo in ambiente fisico (es. Raspberry Pi)
    if [ ! -d "$PROJECT_DIR/venv" ]; then
        echo "Creazione ambiente virtuale..."
        python3 -m venv "$PROJECT_DIR/venv"
    else
        echo "Ambiente virtuale già esistente."
    fi

    # Attivazione venv
    source "$PROJECT_DIR/venv/bin/activate"

    echo "--- 4. Installazione pacchetti Python da requirements.txt ---"
    # Aggiorniamo prima pip e setuptools per evitare problemi con pacchetti binari
    pip install --upgrade pip setuptools wheel

    # Installazione dei requisiti
    pip install -r "$PROJECT_DIR/requirements.txt"
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
    echo "Rilevamento architettura sistema..."
    ARCH=$(uname -m)
    
    if [ "$ARCH" = "x86_64" ]; then
        echo "Architettura rilevata: AMD64 (PC/Codespace). Scaricamento versione x86_64..."
        URL="https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_amd64.tar.gz"
    elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
        echo "Architettura rilevata: ARM64 (Raspberry Pi). Scaricamento versione aarch64..."
        URL="https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_aarch64.tar.gz"
    else
        echo "Errore: Architettura $ARCH non supportata ufficialmente."
        exit 1
    fi

    echo "Scaricamento binari Piper..."
    wget "$URL" -O piper_bundle.tar.gz || exit 1
    tar -xvf piper_bundle.tar.gz
    rm piper_bundle.tar.gz
    
    # Assicuriamoci che il binario sia eseguibile (evita errore 126)
    chmod +x piper/piper
    echo "Installazione Piper completata."
else
    echo "Binari Piper già presenti."
fi

# Scarica il modello Riccardo (VERSIONE X_LOW)
# Nota: La versione Medium non esiste per Riccardo, usiamo x_low che è presente nel repo.
if [ ! -f "it_IT-riccardo-x_low.onnx" ]; then
    echo "Scaricamento modello vocale Riccardo (x_low)..."
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/it/it_IT/riccardo/x_low/it_IT-riccardo-x_low.onnx || exit 1
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/it/it_IT/riccardo/x_low/it_IT-riccardo-x_low.onnx.json || exit 1
else
    echo "Modello Riccardo già presente."
fi

# Scarica il modello PAOLA (MEDIUM) - Scelta finale per qualità e compatibilità
if [ ! -f "it_IT-paola-medium.onnx" ]; then
    echo "Scaricamento modello vocale Paola (Medium)..."
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/it/it_IT/paola/medium/it_IT-paola-medium.onnx || exit 1
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/it/it_IT/paola/medium/it_IT-paola-medium.onnx.json || exit 1
else
    echo "Modello Paola già presente."
fi

echo ""
echo "--- SETUP COMPLETATO ---"
echo "Piper installato in: $PIPER_DEST"
echo "Per avviare Buddy: source venv/bin/activate && python main.py"