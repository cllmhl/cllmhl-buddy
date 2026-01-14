#!/bin/bash
# Test raw della seriale del radar LD2410C
# Legge i dati grezzi in formato hex

echo "🔍 Test Raw Seriale Radar LD2410C"
echo "================================="
echo ""

# Carica configurazione
if [ -f "config.env" ]; then
    set -a
    source config.env
    set +a
fi

RADAR_PORT=${RADAR_PORT:-/dev/ttyAMA10}

echo "📡 Porta: $RADAR_PORT"
echo "📊 Baudrate: 256000"
echo ""

# Verifica che la porta esista
if [ ! -e "$RADAR_PORT" ]; then
    echo "❌ Errore: $RADAR_PORT non esiste!"
    echo "   Porte disponibili:"
    ls -l /dev/tty* | grep -E "(AMA|serial|USB)"
    exit 1
fi

echo "✅ Porta trovata"
echo ""
echo "🔬 Lettura dati grezzi (hex dump)..."
echo "   Premi Ctrl+C per terminare"
echo "   Cerca pattern: FD FC FB FA (header)"
echo ""
echo "-----------------------------------"

# Configura la porta seriale
stty -F "$RADAR_PORT" 256000 cs8 -cstopb -parenb raw

# Leggi e mostra in hex
cat "$RADAR_PORT" | hexdump -C
