#!/bin/bash

# Ottieni la directory del progetto (parent della cartella scripts)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

echo "--- Buddy OS Startup ---"
echo "📂 Script Dir: $SCRIPT_DIR"
echo "📂 Project Dir: $PROJECT_DIR"
echo "🔍 Cerco venv in: $PROJECT_DIR/venv/bin/activate"
if [ -f "$PROJECT_DIR/venv/bin/activate" ]; then
    echo "✅ Trovato!"
else
    echo "❌ Non trovato!"
fi
echo ""

# 1. Gestione Ambiente Virtuale (solo se non siamo in un container)
# Controlla sia Dev Containers (REMOTE_CONTAINERS) che Codespaces (CODESPACES)
if [ -z "$REMOTE_CONTAINERS" ] && [ -z "$CODESPACES" ]; then
    echo "Ambiente fisico rilevato. Attivazione venv..."
    if [ ! -f "$PROJECT_DIR/venv/bin/activate" ]; then
        echo "❌ Errore: Ambiente virtuale non trovato. Esegui prima scripts/setup_buddy.sh"
        exit 1
    fi
    source "$PROJECT_DIR/venv/bin/activate"
else
    echo "Ambiente containerizzato rilevato. Uso Python di sistema."
fi

# 2. Pulizia file temporanei (vecchi mp3 della gTTS rimasti orfani)
rm -f "$PROJECT_DIR"/*.mp3

# 4. Verifica variabili d'ambiente
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "❌ Errore: File .env mancante. È essenziale per le chiavi API."
    echo "Crea il file .env partendo da .env.example e inserisci le tue chiavi."
    exit 1
fi

# 5. Esecuzione di Buddy
# Usiamo 'python3 -u' per forzare l'output non bufferizzato (log più immediati)
python3 -u "$PROJECT_DIR/main.py"

# 6. Disattivazione al termine (solo se abbiamo attivato il venv)
if [ -z "$REMOTE_CONTAINERS" ] && [ -z "$CODESPACES" ]; then
    deactivate
fi
echo "--- Buddy OS Offline ---"
