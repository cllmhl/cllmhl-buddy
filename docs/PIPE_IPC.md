# Buddy Pipe IPC System

Sistema di comunicazione inter-process per testare e controllare Buddy via named pipes Unix.

## 🎯 Panoramica

Due named pipes (FIFO) permettono comunicazione bidirezionale con Buddy:
- **`data/buddy.in`** - Invia comandi/eventi → Buddy
- **`data/buddy.out`** - Ricevi eventi da Buddy ← Buddy

## 🚀 Quick Start

### 1. Avvia Buddy (con config dev.yaml che include gli adapter pipe)

```bash
python main.py --config config/dev.yaml
```

Buddy creerà automaticamente le named pipes in `data/`.

### 2. Avvia il CLI interattivo

```bash
./chat.py
```

Oppure:

```bash
python chat.py
```

## 📋 Comandi Chat CLI

### Comandi Rapidi

```bash
s <testo>       # Speak - Buddy parla
t <testo>       # Talk - Invia speech utente (passa dal Brain)
lon             # LED ON
loff            # LED OFF  
lb <n>          # LED BLINK (n volte, default 3)
```

### Esempi

```bash
> s Ciao, sono Buddy!
✅ Inviato: SPEAK 'Ciao, sono Buddy!'

> lon
✅ Inviato: LED ON

> lb 5
✅ Inviato: LED BLINK x5

> t Hey Buddy, che temperatura c'è?
✅ Inviato: USER_SPEECH 'Hey Buddy, che temperatura c'è?'
```

### Altri Comandi

```bash
menu            # Mostra menu completo
help            # Guida dettagliata
json            # Invia JSON custom
test            # Sequenza test LED+Voce
quit/exit       # Esci
```

## 🔧 Formato Eventi

### DIRECT_OUTPUT Event

Bypassa il Brain e invia direttamente un OutputEvent:

```json
{
  "type": "direct_output",
  "priority": "high",
  "content": {
    "event_type": "speak",
    "content": "Hello World!",
    "priority": "high"
  }
}
```

### USER_SPEECH Event

Passa attraverso il Brain (risposta via LLM):

```json
{
  "type": "user_speech",
  "priority": "high",
  "content": "Che temperatura fa?"
}
```

### Eventi Output Supportati (via DIRECT_OUTPUT)

- `speak` - Emetti voce
- `led_on` - Accendi LED
- `led_off` - Spegni LED
- `led_blink` - Lampeggia LED (content = numero lampeggi)
- `save_history` - Salva in DB history
- `save_memory` - Salva in memoria persistente

## 🎨 Output Monitor

Il CLI mostra in real-time gli eventi emessi da Buddy:

```
🔊 14:23:45 SPEAK → Ciao, la temperatura è 22°C
💡 14:23:50 LED_BLINK → 3
💾 14:24:00 SAVE_HISTORY → conversation_data
```

## 🏗️ Architettura

```
chat.py                          Buddy (main.py)
   |                                    |
   |  JSON → data/buddy.in ──────→ PipeInputAdapter
   |                                    ↓
   |                               EventRouter
   |                                    ↓
   |                                  Brain
   |                                    ↓
   |                               EventRouter
   |                                    ↓
   |  JSON ← data/buddy.out ←───── PipeOutputAdapter
   |
 Monitor
```

## 🧪 Test Hardware

Esempio test completo LED + Voce:

```bash
> test
🧪 Avvio test sequence...
  → LED ON...
  → SPEAK...
  → LED BLINK x2...
  → SPEAK...
  → LED OFF...
✅ Test completato!
```

## 📝 Note Tecniche

- **Named Pipes**: Bloccanti in lettura, non-bloccanti in scrittura
- **JSON Line-Delimited**: Un evento = una linea JSON
- **Event Filtering**: PipeOutputAdapter filtrabile per tipo evento (vedi config)
- **No Reader**: Se nessuno legge da buddy.out, eventi vengono scartati silenziosamente

## 🔍 Debugging

### Verifica pipe esistenti

```bash
ls -la data/
prw-r--r-- 1 user user 0 Jan 18 14:20 buddy.in|
prw-r--r-- 1 user user 0 Jan 18 14:20 buddy.out|
```

Il `p` e `|` indicano che sono named pipes (FIFO).

### Test manuale pipe

Scrittura diretta (senza chat.py):

```bash
echo '{"type":"direct_output","content":{"event_type":"speak","content":"Test"}}' > data/buddy.in
```

Lettura diretta:

```bash
cat data/buddy.out
```

### Troubleshooting

**Errore: "Pipe non trovata"**
- Buddy deve essere avviato PRIMA di chat.py
- Le pipe vengono create automaticamente da Buddy

**Evento non arriva**
- Verifica che PipeInputAdapter sia in config/dev.yaml
- Controlla i log di Buddy

**Output non visibile**
- Verifica che PipeOutputAdapter sia configurato
- Controlla `event_types` filter in config

## 🎯 Use Cases

1. **Test Hardware Rapidi**: Testa LED, speaker senza modificare codice
2. **Debug Events**: Monitora il flusso di eventi real-time
3. **Scripting**: Automatizza test con script bash/python
4. **Remote Control**: Controlla Buddy da processi esterni
5. **Development**: Sviluppa nuove features testando events isolati

## 🚧 Limitazioni

- Solo locale (Unix named pipes)
- Un writer/reader alla volta per pipe
- No persistenza: eventi non letti vengono persi
- No autenticazione/sicurezza

## 🔮 Estensioni Future

- [ ] TCP socket per accesso remoto
- [ ] WebSocket per UI web
- [ ] Event replay da file
- [ ] Event recording/playback
