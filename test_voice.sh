#!/bin/bash

# Uscire in caso di errore
set -e

# --- 1. DEFINIZIONE PERCORSI ---
HOME_DIR="$HOME"
PIPER_BIN="$HOME_DIR/buddy_tools/piper/piper/piper"
MODELS_DIR="$HOME_DIR/buddy_tools/piper"
CONFIG_FILE="config.env"

# --- 2. LETTURA CONFIGURAZIONE ---
# Cerchiamo la variabile TTS_VOICE dentro config.env
# Se non la trova, usa "paola" come fallback
if [ -f "$CONFIG_FILE" ]; then
    # Grep trova la riga, cut prende il valore dopo l'uguale, tr rimuove spazi e virgolette
    VOICE=$(grep "^TTS_VOICE" "$CONFIG_FILE" | cut -d '=' -f2 | tr -d ' "' | tr '[:upper:]' '[:lower:]')
    echo "--- Configurazione letta: Voce impostata su '$VOICE' ---"
else
    echo "⚠️  config.env non trovato. Uso default: paola"
    VOICE="paola"
fi

# --- 3. SELEZIONE PARAMETRI MODELLO ---
if [[ "$VOICE" == "riccardo" ]]; then
    MODEL_FILE="$MODELS_DIR/it_IT-riccardo-x_low.onnx"
    SPEED="1.1"     # Rallenta Riccardo del 10%
    DESC="Riccardo (x_low - 16kHz)"
else
    # Default: Paola
    MODEL_FILE="$MODELS_DIR/it_IT-paola-medium.onnx"
    SPEED="1.0"     # Paola è naturale
    DESC="Paola (Medium - 22kHz)"
fi

# --- 4. CONTROLLI PRELIMINARI ---
if [ ! -f "$PIPER_BIN" ]; then
    echo "❌ Errore: Eseguibile Piper non trovato in $PIPER_BIN"
    exit 1
fi

if [ ! -f "$MODEL_FILE" ]; then
    echo "❌ Errore: Modello vocale non trovato: $MODEL_FILE"
    echo "   Hai eseguito setup_buddy.sh per scaricare entrambi i modelli?"
    exit 1
fi

# Verifica SoX (fondamentale per il fix 48kHz)
if ! command -v sox &> /dev/null; then
    echo "❌ Errore: SoX non installato. Esegui: sudo apt-get install sox libsox-fmt-all"
    exit 1
fi

# --- 5. ESECUZIONE TEST ---
TEXT="Ciao, questo è un test dello script Bash. Sto usando la voce di $VOICE con la catena SoX."

echo "🎤 Avvio test audio..."
echo "   Modello: $DESC"
echo "   Speed:   $SPEED"
echo "   Pipeline: Piper -> SoX (48kHz) -> Aplay (Jabra)"

# La Pipeline Magica:
# 1. Piper genera WAV (al rate nativo del modello)
# 2. SoX converte al volo a 48000Hz (per il Jabra)
# 3. Aplay riproduce sul device hardware plughw:0,0
echo "$TEXT" | "$PIPER_BIN" --model "$MODEL_FILE" --length_scale "$SPEED" --output_file - | sox -t wav - -r 48000 -t wav - | aplay -D plughw:0,0

echo "✅ Test completato."
