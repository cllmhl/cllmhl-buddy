#!/bin/bash

# Definiamo il percorso della cartella
BUDDY_DIR="/home/cllmhl/cllmhl-buddy"

echo "--- 🔄 Aggiornamento Buddy OS ---"

# Entriamo nella cartella
cd "$BUDDY_DIR" || { echo "❌ Errore: Cartella non trovata"; exit 1; }

# 1. Git Pull
echo "[1/2] Recupero sorgenti da Git..."
git fetch --all
git reset --hard origin/main  # Forza la sovrascrittura

# 2. Esecuzione Setup
if [ -f "scripts/setup_buddy.sh" ]; then
    echo "[2/2] Esecuzione setup_buddy.sh..."
    chmod +x scripts/setup_buddy.sh
    bash scripts/setup_buddy.sh
else
    echo "⚠️ Avviso: scripts/setup_buddy.sh non trovato in $BUDDY_DIR"
fi

echo "--- ✅ Operazione completata ---"
