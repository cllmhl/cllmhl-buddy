#!/bin/bash

# Naviga nella cartella del progetto (utile se lanciato da fuori)
cd "$(dirname "$0")"

echo "--- Buddy OS Startup ---"

# 1. Gestione Ambiente Virtuale (solo se non siamo in un container)
# La variabile REMOTE_CONTAINERS è impostata da VS Code.
if [ -z "$REMOTE_CONTAINERS" ]; then
    echo "Ambiente fisico rilevato. Attivazione venv..."
    if [ ! -f "venv/bin/activate" ]; then
        echo "Errore: Ambiente virtuale non trovato. Esegui prima ./setup_buddy.sh"
        exit 1
    fi
    source venv/bin/activate
fi

# 2. Pulizia file temporanei (vecchi mp3 della gTTS rimasti orfani)
rm -f *.mp3

# 4. Verifica variabili d'ambiente
if [ ! -f .env ]; then
    echo "Errore: File .env mancante. È essenziale per le chiavi API."
    echo "Crea il file .env partendo da .env.example e inserisci le tue chiavi."
    exit 1
fi

# 5. Esecuzione di Buddy
# Usiamo 'python3 -u' per forzare l'output non bufferizzato (log più immediati)
python3 -u main.py

# 6. Disattivazione al termine (solo se abbiamo attivato il venv)
if [ -z "$REMOTE_CONTAINERS" ]; then
    deactivate
fi
echo "--- Buddy OS Offline ---"
