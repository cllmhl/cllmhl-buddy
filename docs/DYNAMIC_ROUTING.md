# Dynamic Event Routing

## Problema Originale

Nel design iniziale, il routing degli eventi era gestito da un **dictionary statico** `EVENT_TO_CHANNEL`:

```python
# ❌ VECCHIO APPROCCIO - Statico e ridondante
EVENT_TO_CHANNEL: dict[EventType, OutputChannel] = {
    EventType.SPEAK: OutputChannel.VOICE,
    EventType.LED_ON: OutputChannel.LED,
    EventType.LED_OFF: OutputChannel.LED,
    EventType.LED_BLINK: OutputChannel.LED,
    EventType.SAVE_HISTORY: OutputChannel.DATABASE,
    EventType.SAVE_MEMORY: OutputChannel.DATABASE,
}
```

### Problemi

1. **Ridondanza**: Le informazioni sono duplicate - ogni Port già dichiara cosa gestisce via `handled_events()`
2. **Accoppiamento**: Il core conosce tutti gli eventi possibili anche se alcuni adapter non sono configurati
3. **Sincronizzazione**: Rischio che `EVENT_TO_CHANNEL` vada fuori sync con le dichiarazioni delle Port
4. **Rigidità**: Non si adatta agli adapter effettivamente configurati

## Soluzione: Routing Dinamico

Il routing viene ora costruito **dinamicamente** interrogando gli adapter configurati:

```python
# ✅ NUOVO APPROCCIO - Dinamico e flessibile
def build_event_routing_from_adapters(output_adapters: list) -> dict[EventType, OutputChannel]:
    """
    Costruisce dinamicamente il mapping EventType -> OutputChannel
    interrogando gli adapter OUTPUT effettivamente configurati.
    """
    mapping = {}
    
    for adapter in output_adapters:
        channel = adapter.channel_type
        # Ottieni gli eventi gestiti dalla classe Port dell'adapter
        handled = adapter.__class__.handled_events()
        
        for event_type in handled:
            mapping[event_type] = channel
    
    return mapping
```

## Come Funziona

### 1. Le Port Dichiarano Cosa Gestiscono

```python
class VoiceOutputPort(OutputPort):
    @classmethod
    def handled_events(cls):
        """Eventi gestiti da questa Port"""
        return [EventType.SPEAK]

class LEDOutputPort(OutputPort):
    @classmethod
    def handled_events(cls):
        """Eventi gestiti da questa Port"""
        return [EventType.LED_ON, EventType.LED_OFF, EventType.LED_BLINK]
```

### 2. Gli Adapter Sono Configurati

```yaml
# adapter_config_test.yaml
adapters:
  output:
    voice:
      implementation: "mock_voice"
    led:
      implementation: "mock_led"
    database:
      implementation: "mock_db"
```

### 3. Il Routing Viene Costruito All'Avvio

```python
# main_new.py
def _setup_routes(self):
    # Crea gli adapter dalla configurazione
    self._create_adapters()
    
    # Costruisci routing dinamico dagli adapter configurati
    event_routing = build_event_routing_from_adapters(self.output_adapters)
    
    # Registra le route nel router
    for event_type, channel in event_routing.items():
        if channel in queue_map:
            self.router.register_route(event_type, queue_map[channel], ...)
```

## Vantaggi

### ✅ Zero Ridondanza
Le informazioni sono dichiarate **una sola volta** nelle Port tramite `handled_events()`:

```python
# Prima: 2 posti dove dichiarare
# 1. VoiceOutputPort.handled_events() → [SPEAK]
# 2. EVENT_TO_CHANNEL[SPEAK] = VOICE

# Dopo: 1 posto dove dichiarare
# 1. VoiceOutputPort.handled_events() → [SPEAK]
# Il routing viene costruito automaticamente!
```

### ✅ Adattabilità

Il routing si adatta automaticamente agli adapter configurati:

```python
# Test con solo Voice
adapters = [MockVoiceOutput("voice", {})]
routing = build_event_routing_from_adapters(adapters)
# routing = {EventType.SPEAK: OutputChannel.VOICE}

# Prod con Voice + LED + Database
adapters = [
    JabraVoiceOutput("voice", {...}),
    LEDOutput("led", {...}),
    DatabaseOutput("db", {...})
]
routing = build_event_routing_from_adapters(adapters)
# routing = {
#     EventType.SPEAK: OutputChannel.VOICE,
#     EventType.LED_ON: OutputChannel.LED,
#     EventType.LED_OFF: OutputChannel.LED,
#     EventType.LED_BLINK: OutputChannel.LED,
#     EventType.SAVE_HISTORY: OutputChannel.DATABASE,
#     EventType.SAVE_MEMORY: OutputChannel.DATABASE,
# }
```

### ✅ Single Source of Truth

Le Port sono l'**unica fonte di verità**:

```python
# Vuoi sapere quali eventi gestisce Voice?
events = VoiceOutputPort.handled_events()

# Vuoi sapere dove va l'evento SPEAK?
# Viene dedotto automaticamente dal routing dinamico
```

### ✅ Impossibile Andare Fuori Sync

Non c'è più un dictionary statico da mantenere sincronizzato:

```python
# ❌ Prima: potevi modificare handled_events() e dimenticare EVENT_TO_CHANNEL
class VoiceOutputPort:
    @classmethod
    def handled_events(cls):
        return [EventType.SPEAK, EventType.NEW_EVENT]  # +NEW_EVENT

EVENT_TO_CHANNEL = {
    EventType.SPEAK: OutputChannel.VOICE,
    # ⚠️ Manca NEW_EVENT! Out of sync!
}

# ✅ Dopo: è impossibile andare fuori sync
# Aggiungi NEW_EVENT a handled_events() e il routing si aggiorna automaticamente!
```

### ✅ Testing Facilitato

Ogni test può configurare esattamente gli adapter necessari:

```python
def test_only_voice():
    adapters = [MockVoiceOutput("voice", {})]
    routing = build_event_routing_from_adapters(adapters)
    # Solo eventi voice nel routing!
    
def test_full_system():
    adapters = [voice, led, db]
    routing = build_event_routing_from_adapters(adapters)
    # Tutti gli eventi disponibili!
```

## Architettura

Il flusso completo:

```
1. Configurazione YAML
   ↓
2. AdapterFactory crea gli adapter
   ↓
3. build_event_routing_from_adapters() interroga gli adapter
   ↓
4. Ogni adapter.handled_events() dichiara cosa gestisce
   ↓
5. Costruzione mapping EventType → OutputChannel
   ↓
6. EventRouter.register_route() per ogni mapping
   ↓
7. Sistema pronto a routare eventi dinamicamente!
```

## Relazione con Hexagonal Architecture

Questo design rispetta perfettamente l'architettura esagonale:

- **Core**: Definisce `EventType` e `OutputChannel` (domini puri)
- **Ports**: Dichiarano cosa gestiscono via `handled_events()` (interfacce)
- **Adapters**: Implementano le Port e vengono configurati (implementazioni)
- **Orchestrator**: Costruisce il routing interrogando gli adapter (wiring)

Il **Core non conosce gli adapter**, ma gli adapter implementano le Port del Core:

```
Core/Events.py (EventType, OutputChannel)
    ↑
Adapters/Ports.py (VoiceOutputPort.handled_events())
    ↑
Adapters/Output/voice_output.py (MockVoiceOutput, JabraVoiceOutput)
    ↑
main_new.py (interroga gli adapter per costruire routing)
```

## Migrazione

Per migrare da `EVENT_TO_CHANNEL` a routing dinamico:

1. ✅ Rimosso `EVENT_TO_CHANNEL` da `core/events.py`
2. ✅ Rimosso `get_output_channel()` (non più necessario)
3. ✅ Rinominato `build_event_routing_from_ports()` → `build_event_routing_from_adapters()`
4. ✅ Aggiornato `main_new.py` per costruire routing dinamicamente
5. ✅ Aggiornati i test per validare routing dinamico
6. ✅ Aggiornata la documentazione

## Conclusione

Il routing dinamico elimina la ridondanza e rende il sistema più flessibile e manutenibile:

- **Prima**: Dichiaravi gli eventi in 2 posti (Port + EVENT_TO_CHANNEL)
- **Dopo**: Dichiari in 1 solo posto (Port.handled_events())

- **Prima**: Routing statico uguale per tutti gli ambienti
- **Dopo**: Routing adattato agli adapter effettivamente configurati

- **Prima**: Rischio di andare fuori sync
- **Dopo**: Impossibile andare fuori sync

È l'applicazione pratica del principio **DRY** (Don't Repeat Yourself) e del **Single Source of Truth**.
