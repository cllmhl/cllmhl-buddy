#!/bin/bash
# Test script per i sensori fisici di Buddy

echo "🧪 Test BuddySenses - Radar LD2410C e DHT11"
echo "============================================="
echo ""

# Attiva l'ambiente Python se presente
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Verifica dipendenze
echo "📦 Verifica dipendenze..."
python3 -c "import serial; import adafruit_dht; import board" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Alcune librerie mancano. Installazione..."
    pip3 install -r requirements.txt
fi

echo ""
echo "🚀 Avvio test sensori..."
echo "   - Premi Ctrl+C per terminare"
echo ""

# Carica variabili d'ambiente se config.env esiste
if [ -f "config.env" ]; then
    set -a
    source config.env
    set +a
fi

# Esegui il test script
python3 test_senses.py
