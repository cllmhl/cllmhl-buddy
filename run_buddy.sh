#!/bin/bash

# Naviga nella cartella del progetto (utile se lanciato da fuori)
cd "$(dirname "$0")"

echo "--- Buddy OS Startup ---"

# 1. Verifica se l'ambiente virtuale esiste
if [ ! -d "venv" ]; then
    echo "Errore: Ambiente virtuale non trovato. Esegui prima ./setup_buddy.sh"
    exit 1
fi

# 2. Attivazione ambiente
source venv/bin/activate

# 3. Pulizia file temporanei (vecchi mp3 della gTTS rimasti orfani)
rm -f *.mp3

# 4. Verifica variabili d'ambiente
if [ ! -f ".env" ]; then
    echo "Attenzione: File .env mancante. Verifica le chiavi API."
fi

# 5. Esecuzione di Buddy
# Usiamo 'python3 -u' per forzare l'output non bufferizzato (log più immediati)
python3 -u main.py

# 6. Disattivazione al termine
deactivate
echo "--- Buddy OS Offline ---"
