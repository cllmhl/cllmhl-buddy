#!/bin/bash

# ============================================================================
# Buddy Launcher con BUDDY_HOME
# Gestisce path assoluti evitando problemi di working directory
# ============================================================================

# Ottieni la directory del progetto (parent della cartella scripts)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export BUDDY_HOME="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configura path del config (può essere sovrascritto da .env)
export BUDDY_CONFIG="${BUDDY_CONFIG:-config/adapter_config_dev.yaml}"

echo "--- Buddy OS Startup ---"
echo "🏠 BUDDY_HOME: $BUDDY_HOME"
echo "📋 BUDDY_CONFIG: $BUDDY_CONFIG"
echo ""

# 1. Gestione Ambiente Virtuale (solo se non siamo in un container)
# Controlla sia Dev Containers (REMOTE_CONTAINERS) che Codespaces (CODESPACES)
if [ -z "$REMOTE_CONTAINERS" ] && [ -z "$CODESPACES" ]; then
    echo "Ambiente fisico rilevato. Attivazione venv..."
    if [ ! -f "$BUDDY_HOME/venv/bin/activate" ]; then
        echo "❌ Errore: Ambiente virtuale non trovato. Esegui prima scripts/setup_buddy.sh"
        exit 1
    fi
    source "$BUDDY_HOME/venv/bin/activate"
else
    echo "Ambiente containerizzato rilevato. Uso Python di sistema."
fi

# 2. Pulizia file temporanei (vecchi mp3 della gTTS rimasti orfani)
rm -f "$BUDDY_HOME"/*.mp3

# 3. Carica .env (se esiste) - DOPO aver impostato BUDDY_HOME
if [ -f "$BUDDY_HOME/.env" ]; then
    echo "📄 Caricamento .env..."
    set -a  # Auto-export delle variabili
    source "$BUDDY_HOME/.env"
    set +a
else
    echo "⚠️  File .env non trovato. Assicurati che BUDDY_CONFIG sia impostato."
fi

# 4. Esecuzione di Buddy (usiamo main.py con architettura esagonale)
# NON cambiamo directory - usiamo path assoluti
echo ""
echo "🚀 Avvio Buddy..."
python3 -u "$BUDDY_HOME/main.py"

# 5. Disattivazione al termine (solo se abbiamo attivato il venv)
if [ -z "$REMOTE_CONTAINERS" ] && [ -z "$CODESPACES" ]; then
    deactivate
fi

echo ""
echo "--- Buddy OS Offline ---"
