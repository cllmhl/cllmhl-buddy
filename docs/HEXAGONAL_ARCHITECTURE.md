# Buddy - Hexagonal Architecture Refactor

## 🎯 Obiettivo

Refactoring completo di Buddy usando **Architettura Esagonale (Ports & Adapters)** con **Event-Driven Pattern** e **Event Router**.

## 🏗️ Architettura

```
┌─────────────────────────────────────────────────────────┐
│                   ADAPTER LAYER                         │
├──────────────────────┬──────────────────────────────────┤
│  INPUT (Primary)     │   OUTPUT (Secondary)             │
│                      │                                  │
│  ┌────────────────┐  │   ┌────────────────┐            │
│  │ Voice Input    │  │   │ Voice Output   │            │
│  │ - Jabra/Mock   │  │   │ - Jabra/Log    │            │
│  ├────────────────┤  │   ├────────────────┤            │
│  │ Keyboard Input │  │   │ LED Output     │            │
│  │ - Stdin/Pipe   │  │   │ - GPIO/Mock    │            │
│  ├────────────────┤  │   ├────────────────┤            │
│  │ Sensor Input   │  │   │ Database       │            │
│  │ - Physical/Mock│  │   │ - SQLite+Chroma│            │
│  └────────────────┘  │   ├────────────────┤            │
│         │            │   │ Log Output     │            │
│         ▼            │   │ - File/Console │            │
│  ┌─────────────┐    │   └────────────────┘            │
│  │ Input Queue │    │          ▲                       │
│  │  (Priority) │    │          │                       │
│  └─────────────┘    │   ┌──────────────┐              │
│         │            │   │ Event Router │              │
│         │            │   │ (Dispatcher) │              │
│         ▼            │   └──────────────┘              │
├─────────────────────────────────────────────────────────┤
│                     CORE (Business Logic)               │
│                                                         │
│  ┌──────────────────────────────────────┐              │
│  │           BUDDY BRAIN                │              │
│  │  - Process events                    │              │
│  │  - LLM interaction                   │              │
│  │  - Decision making                   │              │
│  │  - Emit output events                │              │
│  └──────────────────────────────────────┘              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## ✨ Vantaggi Chiave

### 1. **Disaccoppiamento Totale**
- Il Brain NON conosce gli adapter
- Facile sostituire implementazioni (Jabra → Mock)
- Testing in isolamento senza hardware

### 2. **Event Router Pattern**
- Il Brain emette eventi generici
- Il Router smista agli adapter giusti
- Un evento può andare a N destinazioni (broadcast)

### 3. **Priority Queue**
- Eventi con priorità (CRITICAL, HIGH, NORMAL, LOW)
- Emergenze saltano la fila
- Gestione "STOP!" durante speech

### 4. **Port Pattern**
- Interfacce astratte (InputPort, OutputPort)
- Implementazioni multiple per adapter
- Factory crea istanze da configurazione

### 5. **Configuration-Driven**
- Test mode: Mock adapters, no hardware
- Prod mode: Real hardware
- Switch via YAML config

## 📁 Struttura Progetto

```
cllmhl-buddy/
├── core/                          # Business Logic (zero dipendenze)
│   ├── events.py                  # Event system + priorities
│   ├── event_router.py            # Router intelligente
│   └── brain.py                   # Brain puro
│
├── adapters/                      # Ports & Implementations
│   ├── ports.py                   # Interfacce astratte
│   ├── factory.py                 # Factory pattern
│   ├── input/                     # Primary adapters
│   └── output/                    # Secondary adapters
│
├── config/                        # Configuration
│   ├── config_loader.py           # YAML loader
│   ├── adapter_config_test.yaml   # Test mode config
│   └── adapter_config_prod.yaml   # Production config
│
├── tests/                         # Unit tests
│   ├── test_core.py               # Core tests
│   ├── test_adapters.py           # Adapter tests
│   └── test_config.py             # Config tests
│
├── main_new.py                    # New orchestrator
└── [old files...]                 # To be migrated
```

## 🚀 Usage

### Test Mode (No Hardware)

```bash
# Usa config di test (mock adapters)
export BUDDY_CONFIG=config/adapter_config_test.yaml
python main_new.py
```

### Production Mode (Raspberry Pi)

```bash
# Usa config produzione (hardware reale)
export BUDDY_CONFIG=config/adapter_config_prod.yaml
python main_new.py
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_core.py -v

# Run with coverage
pytest tests/ --cov=core --cov=adapters
```

**Test Results:** ✅ 28/28 passing

## 📋 Event Flow

### Input Flow
```
User speaks → Jabra Mic → VoiceInputAdapter
                          ↓
                    Creates Event(USER_SPEECH)
                          ↓
                    Input Queue (Priority)
                          ↓
                    Brain.process_event()
                          ↓
                Returns List[Event] (output events)
                          ↓
                    EventRouter.route_events()
                          ↓
          ┌────────────┬──────────┬──────────┐
          ▼            ▼          ▼          ▼
    Voice Queue  LED Queue  DB Queue  Log Queue
          ▼            ▼          ▼          ▼
    VoiceOutput  LEDOutput  DBOutput  LogOutput
```

### Event Types

**Input Events:**
- `USER_SPEECH` - Voice input
- `KEYBOARD_INPUT` - Keyboard input
- `PIPE_COMMAND` - Named pipe command
- `SENSOR_*` - Sensor data

**Output Events:**
- `SPEAK` - Voice output
- `LED_ON/OFF/BLINK` - LED control
- `SAVE_HISTORY/MEMORY` - Database operations
- `LOG_*` - Logging

## 🔧 Configuration Example

```yaml
# config/adapter_config_test.yaml
adapters:
  input:
    voice:
      implementation: "mock"  # No real hardware
      config:
        source: "/tmp/voice_input.pipe"
    
    keyboard:
      implementation: "stdin"
      config: {}
  
  output:
    voice:
      implementation: "log"  # Write to file instead of speak
      config:
        log_file: "/tmp/voice_output.log"
    
    led:
      implementation: "mock"  # Console output
      config: {}
```

## 🎯 Next Steps (Fase 5)

Migrazione adapters esistenti:

### Input Adapters da Creare
- [ ] `VoiceInputAdapter` (Jabra + Porcupine)
- [ ] `MockVoiceInputAdapter` (da pipe/file)
- [ ] `KeyboardInputAdapter` (stdin)
- [ ] `PipeInputAdapter` (named pipe)
- [ ] `SensorInputAdapter` (radar + DHT11)
- [ ] `MockSensorInputAdapter` (fake data)

### Output Adapters da Creare
- [ ] `VoiceOutputAdapter` (Jabra TTS)
- [ ] `MockVoiceOutputAdapter` (log file)
- [ ] `LEDOutputAdapter` (GPIO)
- [ ] `MockLEDOutputAdapter` (console)
- [ ] `DatabaseOutputAdapter` (SQLite + ChromaDB)
- [ ] `LogOutputAdapter` (file + console)

### Registrazione nel Factory

```python
# In adapters/input/__init__.py
from .voice_input import JabraVoiceInput, MockVoiceInput
from adapters import AdapterFactory

AdapterFactory.register_input("jabra", JabraVoiceInput)
AdapterFactory.register_input("mock", MockVoiceInput)
# ... etc
```

## 📊 Test Coverage

- ✅ Event system and priorities
- ✅ EventRouter routing logic
- ✅ Brain processing (with mock LLM)
- ✅ Port interfaces
- ✅ AdapterFactory creation
- ✅ ConfigLoader parsing

## 🔍 Design Principles

1. **Separation of Concerns**: Core vs Adapters vs Config
2. **Dependency Inversion**: Brain depends on abstractions, not implementations
3. **Open/Closed**: Open for extension (new adapters), closed for modification
4. **Single Responsibility**: Each class has one reason to change
5. **Interface Segregation**: Minimal port interfaces

## 📝 Notes

- Il vecchio `main.py` rimane intatto
- Migrazione graduale adapter per adapter
- Backward compatibility con `buddy_config.json`
- Config YAML override env variables

---

**Status:** 🚧 FASE 4 COMPLETATA - Ready for Fase 5 (Adapter Migration)
