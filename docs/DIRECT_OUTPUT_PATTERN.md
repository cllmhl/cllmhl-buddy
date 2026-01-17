# DIRECT_OUTPUT Pattern

## 🎯 Problema

Nel sistema Buddy, gli eventi hanno una direzione semantica:
- **INPUT events** → dall'esterno verso il Brain (USER_SPEECH, SENSOR_*)
- **OUTPUT events** → dal Brain verso il mondo esterno (SPEAK, LED_ON, etc.)

**Problema per i test hardware:**
Come possiamo testare gli output adapter (LED, speaker) senza passare per il Brain/LLM?

## ✅ Soluzione: DIRECT_OUTPUT

`DIRECT_OUTPUT` è un evento **INPUT** speciale che "wrappa" un evento **OUTPUT**.

### Flusso Normale
```
Input Adapter → USER_SPEECH event → Brain (LLM) → SPEAK event → Voice Output
                                      ↓
                                   (elaborazione)
```

### Flusso DIRECT_OUTPUT
```
Console/Test → DIRECT_OUTPUT(SPEAK) → Brain → unwrap → SPEAK event → Voice Output
                     ↑                   ↓
                  (wrapper)         (bypass LLM)
```

## 📦 Struttura

### Evento Wrapper (Input)
```python
direct_event = Event(
    type=EventType.DIRECT_OUTPUT,     # <- Evento INPUT
    content=inner_event,               # <- Contiene un evento OUTPUT
    priority=EventPriority.HIGH,
    source="console"
)
```

### Evento Interno (Output)
```python
inner_event = Event(
    type=EventType.LED_ON,            # <- Evento OUTPUT reale
    content=None,
    metadata={'led': 'ascolto'}
)
```

## 🔧 Implementazione

### 1. Nel Brain (`brain.py`)

Il Brain riconosce `DIRECT_OUTPUT` e lo unwrappa:

```python
def process_event(self, input_event: Event) -> List[Event]:
    if input_event.type == EventType.DIRECT_OUTPUT:
        return self._handle_direct_output(input_event)
    # ... altri eventi

def _handle_direct_output(self, event: Event) -> List[Event]:
    """Unwrap e inoltra direttamente l'evento interno"""
    inner_event = event.content
    
    # Validazione
    if not isinstance(inner_event, Event):
        return []
    
    # Verifica che sia un output event
    if inner_event.type in INPUT_EVENTS:
        return []
    
    # Inoltra direttamente (bypass LLM)
    return [inner_event]
```

### 2. In un Input Adapter (es: ConsoleInput)

```python
# Utente digita: "led ascolto on"
# ConsoleInput crea:

inner = create_output_event(
    event_type=EventType.LED_ON,
    content=None,
    metadata={'led': 'ascolto'}
)

wrapper = create_input_event(
    event_type=EventType.DIRECT_OUTPUT,
    content=inner,  # <- Evento output wrappato
    source="console"
)

self.input_queue.put((wrapper.priority.value, wrapper))
```

### 3. Il Router lo gestisce normalmente

Il Router riceve `LED_ON` come qualsiasi altro output event:
```python
# Brain restituisce: [inner_event] con type=LED_ON
# Router lo smista a GPIOLEDOutput
# LED si accende
```

## 🎓 Vantaggi

### ✅ Semantica Corretta
- `DIRECT_OUTPUT` è un INPUT (viene dall'esterno)
- L'evento interno è un OUTPUT (va agli adapter)
- Nessuna violazione della direzione degli eventi

### ✅ Generico
Non è solo per test, ma utile anche per:
- Comandi diretti da API REST
- Automazioni hardware senza LLM
- Override manuali durante debug
- Controlli di emergenza

### ✅ Pulito
- Zero inquinamento dello spazio eventi (no TEST_LED_ON, TEST_SPEAK)
- Usa eventi esistenti (LED_ON, SPEAK)
- Pattern unico e chiaro

### ✅ Sicuro
- Validazione nel Brain
- Impedisce ricorsione (no DIRECT_OUTPUT dentro DIRECT_OUTPUT)
- Impedisce wrapping di input events

## 📝 Esempi d'Uso

### Test Hardware LED
```python
# Console input
"led ascolto on"  →  DIRECT_OUTPUT(LED_ON) → Brain → LED_ON → GPIO

# Console input
"led blink 3"     →  DIRECT_OUTPUT(LED_BLINK) → Brain → LED_BLINK → GPIO
```

### Test Hardware Voice
```python
# Console input
"parla Ciao"      →  DIRECT_OUTPUT(SPEAK) → Brain → SPEAK → Jabra
```

### API Endpoint (futuro)
```python
# POST /api/led/on
DIRECT_OUTPUT(LED_ON) → Brain → LED_ON → GPIO

# POST /api/tts
DIRECT_OUTPUT(SPEAK) → Brain → SPEAK → Speaker
```

### Automazione
```python
# Regola: "Se temperatura > 25°C, accendi LED rosso"
if temp > 25:
    direct = create_input_event(
        EventType.DIRECT_OUTPUT,
        content=create_output_event(EventType.LED_ON, metadata={'led': 'alert'})
    )
```

## 🚫 Anti-Pattern

### ❌ Non fare
```python
# NON wrappare input events!
DIRECT_OUTPUT(USER_SPEECH)  # ❌ Sbagliato!

# NON wrappare DIRECT_OUTPUT in se stesso!
DIRECT_OUTPUT(DIRECT_OUTPUT(...))  # ❌ Ricorsione!

# NON usare per eventi di sistema
DIRECT_OUTPUT(SHUTDOWN)  # ❌ Pericoloso!
```

### ✅ Fare
```python
# Wrappare solo output events
DIRECT_OUTPUT(LED_ON)      # ✅
DIRECT_OUTPUT(SPEAK)       # ✅
DIRECT_OUTPUT(LED_BLINK)   # ✅
```

## 🧪 Testing

Test unitario:
```bash
python3 tests/test_direct_output.py
```

Test integrazione (quando implementato ConsoleInput):
```bash
cd tests/hardware
python3 run_led_test.py
# Digita: led ascolto on
```

## 📊 Diagramma Completo

```
┌─────────────────┐
│  ConsoleInput   │ (o altro input)
└────────┬────────┘
         │ crea
         ▼
┌────────────────────────────┐
│  Event(DIRECT_OUTPUT)      │ ← Input Event (wrapper)
│  content = Event(LED_ON)   │ ← Output Event (interno)
└────────┬───────────────────┘
         │
         ▼
    ┌────────┐
    │  Brain │
    └───┬────┘
        │ unwrap
        ▼
    ┌─────────────┐
    │ Event(LED_ON)│ ← Output Event
    └──────┬──────┘
           │
           ▼
      ┌─────────┐
      │ Router  │
      └────┬────┘
           │
           ▼
    ┌────────────────┐
    │ GPIOLEDOutput  │
    └────────────────┘
           │
           ▼
       🔵 LED fisico
```

## 🎯 Conclusione

`DIRECT_OUTPUT` è un pattern elegante che:
- Mantiene la semantica input/output corretta
- Bypassa il Brain quando necessario
- È generico (non solo per test)
- È sicuro (validazione nel Brain)
- È estensibile (funziona con tutti gli output events)

Perfetto per test hardware, comandi diretti e automazioni! 🚀
