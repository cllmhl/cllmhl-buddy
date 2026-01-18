#!/bin/bash
# Demo script per Buddy Pipe IPC System

echo "🤖 Buddy Pipe IPC - Script Demo"
echo "================================"
echo ""

# Assicurati che le pipe esistano
if [[ ! -p data/buddy.in ]] || [[ ! -p data/buddy.out ]]; then
    echo "❌ Errore: Buddy non è in esecuzione!"
    echo "   Avvia prima Buddy con: python main.py --config config/dev.yaml"
    exit 1
fi

echo "✅ Pipe trovate, invio comandi..."
echo ""

# Funzione helper per inviare eventi
send_event() {
    echo "$1" > data/buddy.in
    echo "📤 Inviato: $2"
    sleep 1
}

# Test 1: LED ON
send_event '{"type":"direct_output","content":{"event_type":"led_on","content":true}}' "LED ON"

# Test 2: Speak
send_event '{"type":"direct_output","content":{"event_type":"speak","content":"Script demo in esecuzione"}}' "SPEAK"

# Test 3: LED BLINK
send_event '{"type":"direct_output","content":{"event_type":"led_blink","content":3}}' "LED BLINK x3"

# Test 4: LED OFF
send_event '{"type":"direct_output","content":{"event_type":"led_off","content":true}}' "LED OFF"

# Test 5: USER_SPEECH (passa dal Brain)
send_event '{"type":"user_speech","priority":"high","content":"Che ore sono?"}' "USER_SPEECH"

echo ""
echo "✅ Demo completata!"
echo ""
echo "💡 Suggerimento: Usa ./chat.py per un'interfaccia interattiva più comoda"
