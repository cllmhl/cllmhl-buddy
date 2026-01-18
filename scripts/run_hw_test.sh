#!/bin/bash

# ============================================================================
# Hardware Test Runner - Wrapper universale per test hardware
# Gestisce automaticamente venv su Raspberry Pi / nessun venv in devspaces
# ============================================================================

set -e  # Exit on error

# Ottieni la directory del progetto
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export BUDDY_HOME="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "--- Buddy Hardware Test Runner ---"
echo "🏠 BUDDY_HOME: $BUDDY_HOME"
echo ""

# Gestione Ambiente Virtuale (solo se non siamo in un container)
if [ -z "$REMOTE_CONTAINERS" ] && [ -z "$CODESPACES" ]; then
    echo "🔧 Raspberry Pi rilevato. Attivazione venv..."
    if [ ! -f "$BUDDY_HOME/venv/bin/activate" ]; then
        echo "❌ Errore: Ambiente virtuale non trovato."
        echo "   Esegui prima: bash scripts/setup_buddy.sh"
        exit 1
    fi
    source "$BUDDY_HOME/venv/bin/activate"
    echo "✅ venv attivato"
else
    echo "☁️  Devspaces/Container rilevato. Uso Python di sistema."
fi

# Carica .env se esiste
if [ -f "$BUDDY_HOME/.env" ]; then
    echo "📄 Caricamento .env..."
    set -a
    source "$BUDDY_HOME/.env"
    set +a
fi

# Determina quale test eseguire (default: hardware_test)
TEST_SCRIPT="${1:-run_hardware_test.py}"

# Se il parametro non contiene .py, costruisci il nome del file
if [[ ! "$TEST_SCRIPT" =~ \.py$ ]]; then
    # Se contiene già run_ all'inizio, usalo così com'è + .py
    if [[ "$TEST_SCRIPT" =~ ^run_ ]]; then
        TEST_SCRIPT="${TEST_SCRIPT}.py"
    else
        # Altrimenti aggiungi prefisso e suffisso
        TEST_SCRIPT="run_${TEST_SCRIPT}_test.py"
    fi
fi

# Path completo del test
TEST_PATH="$BUDDY_HOME/tests/hardware/$TEST_SCRIPT"

if [ ! -f "$TEST_PATH" ]; then
    echo "❌ Errore: Test non trovato: $TEST_PATH"
    echo ""
    echo "Test disponibili:"
    ls -1 "$BUDDY_HOME/tests/hardware/run_"*.py | xargs -n 1 basename
    exit 1
fi

echo ""
echo "🚀 Esecuzione: $TEST_SCRIPT"
echo ""

# Esegui il test con path assoluti
cd "$BUDDY_HOME/tests/hardware"
python3 "$TEST_PATH"
