# Sistema Eventi - Documentazione Completa

## Architettura Eventi

Il sistema usa un'architettura **event-driven** con routing basato su `EventType`:
- Eventi creati dagli **InputPort** (sensori, voce)
- Eventi processati da **BuddyBrain** (logica centrale)
- Eventi consumati da **OutputPort** (voce, LED, database)

## Struttura Event

```python
@dataclass(order=True)
class Event:
    priority: EventPriority      # CRITICAL, HIGH, NORMAL, LOW
    type: EventType              # Tipo evento (USER_SPEECH, SPEAK, ecc.)
    content: Any                 # Payload principale (vedi sotto)
    timestamp: float             # Timestamp creazione
    source: Optional[str]        # Sorgente evento (es: "radar", "dht11")
    metadata: Optional[dict]     # Dati aggiuntivi (vedi sotto)
```

---

## 📊 Mapping EventType → Port Classes

### INPUT EVENTS

#### `EventType.USER_SPEECH`
- **Emesso da**: `VoiceInputPort` → `JabraVoiceInput`
- **Content**: `str` - testo riconosciuto da speech-to-text
- **Metadata**: non utilizzato (tipicamente vuoto)
- **Priority**: `NORMAL`
- **Esempio**:
  ```python
  Event(
      type=EventType.USER_SPEECH,
      content="Ciao Buddy, che ore sono?",
      source="jabra_voice",
      priority=EventPriority.NORMAL,
      metadata={}
  )
  ```

#### `EventType.SENSOR_PRESENCE`
- **Emesso da**: `RadarInputPort` → `LD2410CRadarInput`
- **Content**: `bool` - True=presenza rilevata, False=assenza
- **Metadata**: `dict` con dati completi radar:
  - `presence`: bool
  - `movement`: bool
  - `static`: bool  
  - `distance`: int (cm) - distanza target
  - `mov_distance`: int (cm)
  - `static_distance`: int (cm)
  - `mov_energy`: int (0-100)
  - `static_energy`: int (0-100)
  - `detection_distance`: int (cm)
- **Priority**: `LOW`
- **Esempio**:
  ```python
  Event(
      type=EventType.SENSOR_PRESENCE,
      content=True,
      source="radar",
      priority=EventPriority.LOW,
      metadata={
          'presence': True,
          'distance': 150,
          'mov_energy': 45,
          'static_energy': 20,
          'movement': True,
          'static': False
      }
  )
  ```

#### `EventType.SENSOR_MOVEMENT`
- **Emesso da**: `RadarInputPort` → `LD2410CRadarInput`
- **Content**: `bool` - True se movimento rilevato
- **Metadata**: stessi dati di SENSOR_PRESENCE
- **Priority**: `LOW`
- **Note**: Emesso solo quando `mov_energy > 15` (filtro rumore)

#### `EventType.SENSOR_TEMPERATURE`
- **Emesso da**: `TemperatureInputPort` → `DHT11TemperatureInput`
- **Content**: `float` - temperatura in °C
- **Metadata**: `dict` con dati completi DHT11:
  - `temperature`: float
  - `humidity`: float
  - `temp_unit`: str ("celsius")
  - `humidity_unit`: str ("percent")
  - `sensor`: str ("DHT11")
  - `read_time`: float (timestamp)
  - `temp_changed`: bool
  - `humidity_changed`: bool
- **Priority**: `LOW`
- **Esempio**:
  ```python
  Event(
      type=EventType.SENSOR_TEMPERATURE,
      content=24.5,
      source="dht11",
      priority=EventPriority.LOW,
      metadata={
          'temperature': 24.5,
          'humidity': 65.0,
          'temp_unit': 'celsius',
          'humidity_unit': 'percent',
          'sensor': 'DHT11',
          'temp_changed': True,
          'humidity_changed': False
      }
  )
  ```

#### `EventType.SENSOR_HUMIDITY`
- **Emesso da**: `TemperatureInputPort` → `DHT11TemperatureInput`
- **Content**: `float` - umidità in %
- **Metadata**: stessi dati di SENSOR_TEMPERATURE
- **Priority**: `LOW`
- **Note**: Attualmente non emesso (DHT11 emette solo SENSOR_TEMPERATURE con humidity in metadata)

---

### OUTPUT EVENTS

#### `EventType.SPEAK`
- **Gestito da**: `VoiceOutputPort` → `JabraVoiceOutput`, `MockVoiceOutput`
- **Content**: `str` - testo da sintetizzare e pronunciare
- **Metadata**: `dict` (opzionale):
  - `triggered_by`: str (es: "user_speech")
- **Priority**: tipicamente `HIGH` (risposta utente) o `CRITICAL` (shutdown)
- **Esempio**:
  ```python
  Event(
      type=EventType.SPEAK,
      content="La temperatura attuale è 24 gradi",
      priority=EventPriority.HIGH,
      metadata={'triggered_by': 'user_speech'}
  )
  ```

#### `EventType.LED_ON`
- **Gestito da**: `LEDOutputPort` → `GPIOLEDOutput`, `MockLEDOutput`
- **Content**: non utilizzato (tipicamente None)
- **Metadata**: `dict` (opzionale):
  - `led`: str - nome LED ("stato", "ascolto", ecc.) - default: "stato"
- **Priority**: `NORMAL`
- **Esempio**:
  ```python
  Event(
      type=EventType.LED_ON,
      content=None,
      priority=EventPriority.NORMAL,
      metadata={'led': 'stato'}
  )
  ```

#### `EventType.LED_OFF`
- **Gestito da**: `LEDOutputPort` → `GPIOLEDOutput`, `MockLEDOutput`
- **Content**: non utilizzato (tipicamente None)
- **Metadata**: come LED_ON
- **Priority**: `NORMAL`

#### `EventType.LED_BLINK`
- **Gestito da**: `LEDOutputPort` → `GPIOLEDOutput`, `MockLEDOutput`
- **Content**: non utilizzato (tipicamente None)
- **Metadata**: come LED_ON
- **Priority**: `NORMAL`

#### `EventType.SAVE_HISTORY`
- **Gestito da**: `DatabaseOutputPort` → `ChromaDatabaseOutput`, `MockDatabaseOutput`
- **Content**: `dict` con struttura:
  - `role`: str - "user" o "model"
  - `text`: str - contenuto messaggio
- **Metadata**: non utilizzato
- **Priority**: `LOW`
- **Esempio**:
  ```python
  Event(
      type=EventType.SAVE_HISTORY,
      content={
          'role': 'user',
          'text': 'Ciao Buddy, come stai?'
      },
      priority=EventPriority.LOW
  )
  ```

#### `EventType.SAVE_MEMORY`
- **Gestito da**: `DatabaseOutputPort` → `ChromaDatabaseOutput`, `MockDatabaseOutput`
- **Content**: `dict` con struttura:
  - `fact`: str - fatto da memorizzare
  - `category`: str - categoria (es: "preferences", "facts")
  - `notes`: str (opzionale) - note aggiuntive
  - `importance`: float (0-1) - importanza del fatto
- **Metadata**: non utilizzato
- **Priority**: `LOW`
- **Esempio**:
  ```python
  Event(
      type=EventType.SAVE_MEMORY,
      content={
          'fact': 'Il mio colore preferito è il blu',
          'category': 'preferences',
          'importance': 0.8
      },
      priority=EventPriority.LOW
  )
  ```

#### `EventType.DISTILL_MEMORY`
- **Gestito da**: `ArchivistOutputPort` → `ArchivistOutput`
- **Content**: `None` (non utilizzato)
- **Metadata**: `dict`:
  - `elapsed_seconds`: float - secondi dall'ultimo trigger
- **Priority**: `LOW`
- **Note**: Triggerato automaticamente da BuddyBrain ogni N secondi (archivist_interval)
- **Esempio**:
  ```python
  Event(
      type=EventType.DISTILL_MEMORY,
      content=None,
      priority=EventPriority.LOW,
      metadata={'elapsed_seconds': 1800.0}
  )
  ```

---

## 🔄 Event Flow

### 1. Input Event Flow
```
[Sensore/Utente] 
    → InputAdapter.emette_evento()
    → input_queue (PriorityQueue condivisa)
    → BuddyBrain.process_event()
    → [genera output_events]
    → EventRouter.route_events()
    → OutputAdapter.output_queue (code individuali)
```

### 2. Output Event Routing

Il routing è **dinamico** basato su `handled_events()`:

```python
# In main.py - BuddyOrchestrator._setup_routes()
for adapter in self.output_adapters:
    for event_type in adapter.__class__.handled_events():
        self.event_router.register_route(event_type, adapter)
```

**Mapping attuale**:
- `SPEAK` → VoiceOutputPort
- `LED_ON, LED_OFF, LED_BLINK` → LEDOutputPort  
- `SAVE_HISTORY, SAVE_MEMORY` → DatabaseOutputPort
- `DISTILL_MEMORY` → ArchivistOutputPort

**Multi-destinazione**: Un evento può essere inviato a **più adapter** (es: SPEAK può andare sia a VoiceOutput che ConsoleOutput).

---

## 📝 Content Type Summary

| EventType | Content Type | Struttura Content |
|-----------|-------------|-------------------|
| `USER_SPEECH` | `str` | Testo riconosciuto |
| `SENSOR_PRESENCE` | `bool` | True/False presenza |
| `SENSOR_MOVEMENT` | `bool` | True/False movimento |
| `SENSOR_TEMPERATURE` | `float` | Temperatura in °C |
| `SENSOR_HUMIDITY` | `float` | Umidità in % |
| `SPEAK` | `str` | Testo da pronunciare |
| `LED_ON/OFF/BLINK` | `None` | Non usato |
| `SAVE_HISTORY` | `dict` | `{role: str, text: str}` |
| `SAVE_MEMORY` | `dict` | `{fact: str, category: str, importance: float}` |
| `DISTILL_MEMORY` | `None` | Non usato |

---

## 📦 Metadata Usage Summary

| EventType | Metadata Keys | Scopo |
|-----------|---------------|-------|
| `USER_SPEECH` | - | Non usato |
| `SENSOR_PRESENCE` | `presence`, `distance`, `mov_energy`, `static_energy`, ... | Dati completi radar |
| `SENSOR_MOVEMENT` | Come SENSOR_PRESENCE | Dati completi radar |
| `SENSOR_TEMPERATURE` | `temperature`, `humidity`, `sensor`, `temp_changed`, ... | Dati completi DHT11 |
| `SPEAK` | `triggered_by` | Indica origine (es: "user_speech") |
| `LED_ON/OFF/BLINK` | `led` | Nome LED target (default: "stato") |
| `SAVE_HISTORY` | - | Non usato |
| `SAVE_MEMORY` | - | Non usato |
| `DISTILL_MEMORY` | `elapsed_seconds` | Tempo dall'ultimo trigger |

---

## 🎯 Priority Guidelines

| Priority | Uso | Esempi |
|----------|-----|--------|
| `CRITICAL` | Emergenze, shutdown | SHUTDOWN, risposta vocale shutdown |
| `HIGH` | Comandi utente diretti | SPEAK (risposta a USER_SPEECH) |
| `NORMAL` | Operazioni normali | LED, eventi generici |
| `LOW` | Background tasks | Sensori, SAVE_HISTORY, DISTILL_MEMORY |

---

## 🔧 Helper Functions

```python
# Per INPUT events (da InputPort)
create_input_event(
    event_type: EventType,
    content: Any,
    source: str,                        # OBBLIGATORIO - identifica sorgente
    priority: EventPriority = NORMAL,
    metadata: Optional[dict] = None
) -> Event

# Per OUTPUT events (da BuddyBrain)
create_output_event(
    event_type: EventType,
    content: Any,
    priority: EventPriority = NORMAL,
    metadata: Optional[dict] = None     # source non richiesto
) -> Event
```

---

## 🧪 Testing Events

Esempi di creazione eventi per testing:

```python
# Test input vocale
voice_event = create_input_event(
    EventType.USER_SPEECH,
    "Ciao Buddy",
    source="test_voice"
)

# Test sensore radar
radar_event = create_input_event(
    EventType.SENSOR_PRESENCE,
    True,
    source="test_radar",
    metadata={'distance': 100, 'mov_energy': 30}
)

# Test output vocale
speak_event = create_output_event(
    EventType.SPEAK,
    "Risposta test",
    priority=EventPriority.HIGH
)
```

---

## 🔍 Event Debugging

Per tracciare eventi in runtime:

```python
# In adapters/output/console_output.py - attivare verbose mode
console = ConsoleOutput("console", {"verbose": True})

# Output dettagliato per ogni evento con metadata completi
```

Log event in BuddyBrain:
```python
logger.debug(f"Processing event: {event}")  # Usa __repr__ di Event
```

---

## 📚 Riferimenti Codice

- **Event Definition**: [core/events.py](../core/events.py)
- **Port Definitions**: [adapters/ports.py](../adapters/ports.py)
- **BuddyBrain Processing**: [core/brain.py](../core/brain.py)
- **Event Router**: [core/event_router.py](../core/event_router.py)
- **Input Adapters**: [adapters/input/](../adapters/input/)
- **Output Adapters**: [adapters/output/](../adapters/output/)
