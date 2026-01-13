#!/bin/bash
# Script helper per inviare comandi a Buddy tramite Named Pipe

PIPE_PATH="/tmp/buddy_pipe"

# Verifica che la pipe esista
if [ ! -p "$PIPE_PATH" ]; then
    echo "❌ Errore: Named Pipe non trovata ($PIPE_PATH)"
    echo "   Buddy è in esecuzione?"
    exit 1
fi

# Se non ci sono argomenti, chiedi input
if [ $# -eq 0 ]; then
    echo "🤖 Buddy Command Interface"
    echo "Scrivi il tuo messaggio (Ctrl+C per uscire):"
    echo ""
    while true; do
        read -p "Tu > " message
        if [ -n "$message" ]; then
            echo "$message" > "$PIPE_PATH"
            echo "✓ Messaggio inviato"
        fi
    done
else
    # Invia il messaggio passato come argomento
    echo "$*" > "$PIPE_PATH"
    echo "✓ Messaggio inviato: $*"
fi
