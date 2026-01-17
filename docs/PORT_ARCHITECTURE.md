# Port Architecture - Self-Contained Event Declarations

## Problema Risolto

Prima avevamo una **triade confusa e disconnessa**:
- `OutputPort` generico con field `channel_type`
- `EventType` (eventi) mappati altrove
- `OutputChannel` (canali) con mapping esterno

**Il problema**: Le Port non dichiaravano cosa gestivano. Il routing era definito lontano dalle classi che lo implementavano.

## Soluzione: Port Autodocumentanti

Ogni Port **dichiara esplicitamente** quali eventi gestisce/emette:

### Output Ports

```python
class VoiceOutputPort(OutputPort):
    @property
    def channel_type(self):
        return OutputChannel.VOICE
    
    @classmethod
    def handled_events(cls):
        """Dichiara quali eventi gestisce"""
        return [EventType.SPEAK]
```

### Input Ports

```python
class VoiceInputPort(InputPort):
    @classmethod
    def emitted_events(cls):
        """Dichiara quali eventi emette"""
        return [EventType.USER_SPEECH]
```

## Signature Complete e Chiare

### Output Ports

## Signature Complete e Chiare

### Output Ports - Dichiarano cosa gestiscono

| Port Class          | Channel    | `handled_events()` ritorna       |
|---------------------|------------|----------------------------------|
| `VoiceOutputPort`   | `VOICE`    | `[EventType.SPEAK]`              |
| `LEDOutputPort`     | `LED`      | `[LED_ON, LED_OFF, LED_BLINK]`   |
| `DatabaseOutputPort`| `DATABASE` | `[SAVE_HISTORY, SAVE_MEMORY]`    |

### Input Ports - Dichiarano cosa emettono

| Port Class              | `emitted_events()` ritorna              |
|-------------------------|-----------------------------------------|
| `VoiceInputPort`        | `[EventType.USER_SPEECH]`               |
| `RadarInputPort`        | `[SENSOR_PRESENCE, SENSOR_MOVEMENT]`    |
| `TemperatureInputPort`  | `[SENSOR_TEMPERATURE, SENSOR_HUMIDITY]` |

### Implementazioni Concrete

### Implementazioni Concrete

**Output Adapters**:

| Port Base            | Implementazioni Reali    | Implementazioni Mock     |
|----------------------|--------------------------|--------------------------|
| `VoiceOutputPort`    |Adapter

### Output Adapter

#### 1. Identifica il Channel Type

Quale canale usi? `VOICE`, `LED`, o `DATABASE`?

#### 2. Estendi la Port Corretta

```python
from adapters.ports import VoiceOutputPort  # o LEDOutputPort, DatabaseOutputPort

class MyCustomVoiceOutput(VoiceOutputPort):
    """La tua implementazione custom"""
    
    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        # Inizializzazione custom
    
    def start(self, output_queue: PriorityQueue) -> None:
        # Avvio adapter - consuma dalla queue
        pass
    
    def stop(self) -> None:
        # Shutdown pulito
        pass
```

**Non devi dichiarare `channel_type` o `handled_events()`** - sono ereditati dalla Port base!

### Input Adapter

#### 1. Identifica il Tipo di Input

Voce, sensore generico, radar, temperatura?

#### 2. Estendi la Port Corretta

```python
from adapters.ports import VoiceInputPort  # o SensorInputPort, RadarInputPort, etc

class MyCustomVoiceInput(VoiceInputPort):
    """La tua implementazione custom"""
    
    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        # Inizializzazione custom
    
   # 3. Registra nella Factory

```python
# In adapters/output/__init__.py o adapters/input/__init__.py
from adapters import AdapterFactory
from .my_custom import MyCustomVoiceOutput

AdapterFactory.register_output("my_custom_voice", MyCustomVoiceOutput)
# oppure
AdapterFactory.register_input("my_custom_voice", MyCustomVoiceInput)
```

#### def start(self, input_queue: PriorityQueue) -> None:
        # Avvio adapter - pubblica sulla queue
        pass
    
    def stop(self) -> None:
        # Shutdown pulito
        pass
```

**Non devi dichiarare `emitted_events()`** - è ereditato dalla Port base!, config)
        # Inizializzazione custom
    
    def start(self, output_queue: PriorityQueue) -> None:
        # Avvio adapter
        pass
    
    def stop(self) -> None:
        # Shutdown pulito
        pass
```

### 3. Registra nella Factory

```python
# In adapters/output/__init__.py o all'avvio
from adapters import AdapterFactory
from .mSelf-Contained
- Ogni Port **dichiara** cosa gestisce/emette
- Non serve cercare mapping esterni
- La signature è nella classe stessa

### 📖 Self-Documenting
- Leggendo `VoiceOutputPort.handled_events()` sai cosa gestisce
- Leggendo `VoiceInputPort.emitted_events()` sai cosa emette
- Documentazione esplicita nel codice

### 🔍 Introspectable
```python
# Scopri cosa gestisce una Port
events = VoiceOutputPort.handled_events()
print(f"VoiceOutputPort gestisce: {events}")

# Scopri cosa emette una Port
events = RadarInputPort.emitted_events()
print(f"RadarInputPort emette: {events}")
```

### ✅ Validabile
- Test verificano che le dichiarazioni siano corrette
- `build_event_routing_from_adapters()` costruisce il routing dinamicamente
- Impossibile avere mapping inconsistenti perché il routing viene costruito dagli adapter configurati
```yaml
adapters:
  output:
    voice:  # ← Nome del CHANNEL
      implementation: "my_custom_voice"  # ← Nome registrato
      config:
        # Config specifica
```

## Validazione Type-Safe

Il sistema ora valida automaticamente:

✅ **Compile-time**: Il tipo della classe Port comunica cosa gestisce  
✅ **Runtime**: La validazione verifica che l'adapter sia configurato nel canale corretto  
### 🧪 Testabile
- Ogni Port type può avere test specifici
- Test verificano che `handled_events()` e `emitted_events()` siano implementati
- Mock separati per ogni tipo di input/output

### 🔧 Manutenibile
- Aggiungi nuovo evento? Aggiungilo in `handled_events()` della Port
- Modifiche localizzate, impatto minimo sul resto del sistema

### 🚀 Estensibile
- Nuovi adapter estendono Port esistenti ed ereditano la signature
- Pattern chiaro e consistente per tutti gli adapter

## Validazione Automatica e Routing Dinamico

Il sistema costruisce il routing **dinamicamente** dagli adapter configurati:

```python
from core import build_event_routing_from_adapters

# Costruisce mapping interrogando gli adapter output configurati
output_adapters = [voice_adapter, led_adapter, db_adapter]
event_routing = build_event_routing_from_adapters(output_adapters)

# Il routing è costruito dai metodi handled_events() delle Port
# event_routing = {
#     EventType.SPEAK: OutputChannel.VOICE,
#     EventType.LED_ON: OutputChannel.LED,
#     ...
# }
```

### Vantaggi del Routing Dinamico

✅ **Zero Accoppiamento**: Nessun dictionary statico da mantenere sincronizzato  
✅ **Single Source of Truth**: Le Port dichiarano cosa gestiscono via `handled_events()`  
✅ **Configurabile**: Il routing si adatta agli adapter effettivamente configurati  
✅ **Testabile**: Ogni ambiente (test/prod) ha il suo routing basato sui suoi adapter  

Questo garantisce che:
- Il routing sia sempre coerente con gli adapter disponibili
- Non ci siano eventi "orfani" senza destinazione
- Il sistema funzioni con qualsiasi combinazione di adapter

## Test Coverage

I test verificano:

✅ Ogni OutputPort dichiara `handled_events()`  
✅ Ogni InputPort dichiara `emitted_events()`  
✅ Eventi dichiarati corrispondono al channel_type  
✅ Il routing può essere costruito dinamicamente dagli adapter  
✅ Nessun overlap tra eventi di Port diverse  

Vedi [tests/test_port_events.py](../tests/test_port_events.py) per dettagli.

**Prima**: Partiva e crashava a runtime  
**Ora**: Errore immediato all'avvio:
```
❌ CONFIGURATION ERROR: Adapter 'led_mock_led' 
has channel_type=LED but is configured under channel 'voice'. 
This is a dangerous mismatch!
```

## Vantaggi del Design

### 🎯 Type Safety
- Il tipo `VoiceOutputPort` comunica esplicitamente il ruolo
- Impossibile assegnare adapter sbagliati senza errore

### 📖 Self-Documenting
- Leggendo `class MyAdapter(VoiceOutputPort)` sai subito cosa fa
- Non serve cercare field nascosti o documentazione

### 🧪 Testabile
- Ogni Port type può avere test specifici
- Mock separati per ogni tipo di output

### 🔧 Manutenibile
- Aggiungi nuovo canale? Crea nuova Port
- Modifiche localizzate, impatto minimo

### 🚀 Estensibile
- Nuovi adapter estendono Port esistenti
- Pattern chiaro e consistente

## Relazione con Event System

Il routing `EventType → OutputChannel` viene costruito **dinamicamente** interrogando gli adapter:

```python
# Il routing è costruito all'avvio dagli adapter configurati
output_adapters = [voice_adapter, led_adapter, db_adapter]
event_routing = build_event_routing_from_adapters(output_adapters)

# Ogni adapter dichiara cosa gestisce tramite handled_events()
# VoiceOutputPort.handled_events() → [EventType.SPEAK]
# LEDOutputPort.handled_events() → [EventType.LED_ON, LED_OFF, LED_BLINK]
# DatabaseOutputPort.handled_events() → [EventType.SAVE_HISTORY, SAVE_MEMORY]
```
    EventType.LED_ON: OutputChannel.LED,
    # ...
}
```

Ogni `OutputChannel` corrisponde a una Port specializzata:
- `OutputChannel.VOICE` → `VoiceOutputPort`
- `OutputChannel.LED` → `LEDOutputPort`
- `OutputChannel.DATABASE` → `DatabaseOutputPort`

Questa triade ora ha **signature chiare** e **relazioni esplicite**.
