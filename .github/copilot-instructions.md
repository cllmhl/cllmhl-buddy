# Buddy AI Assistant - Copilot Instructions

## Project Overview
Buddy is a Raspberry Pi-based AI assistant with physical sensors (radar, temperature/humidity, voice I/O) using **Hexagonal Architecture** with an **Event-Driven system**. The core business logic (Brain + Archivist) is decoupled from I/O via **Input/Output Ports**.

## Architecture Pattern: Hexagonal (Ports & Adapters)

### Core Components (Pure Business Logic)
- **[core/brain.py](core/brain.py)**: LLM processing (Google Gemini) - consumes `InputEvent`, produces `List[OutputEvent]`
- **[core/archivist.py](core/archivist.py)**: Memory distillation using LLM to extract facts from conversation history
- **[core/event_router.py](core/event_router.py)**: Routes output events to registered adapters (1:N mapping)
- **[core/events.py](core/events.py)**: Event definitions split into `InputEventType` (from world) and `OutputEventType` (to world)

### Adapter Layer
- **[adapters/ports.py](adapters/ports.py)**: Abstract base classes (`InputPort`, `OutputPort`) with specialized ports (`VoiceInputPort`, `RadarInputPort`, etc.)
- **[adapters/factory.py](adapters/factory.py)**: Dynamic adapter instantiation from YAML config using `getattr()` lookup
- **[adapters/input/](adapters/input/)**: Primary adapters (pipe, voice, radar, temperature sensors)
- **[adapters/output/](adapters/output/)**: Secondary adapters (console, voice, LED, database, archivist)

### Orchestration
- **[main.py](main.py)**: `BuddyOrchestrator` - initializes components, runs main event loop, manages lifecycle

## Code Quality: Fail-Fast Philosophy

**ALWAYS generate fail-fast code**. Never tolerate errors silently:

| Aspect | ❌ Avoid (Tollerante) | ✅ Required (Fail Fast) |
|--------|----------------------|-------------------------|
| **Configuration** | `get(key, default)` | `config.key` - Crash if missing |
| **Types** | `Optional[str] = None` | `str` - No optionals without reason |
| **Exceptions** | `except: pass` | `except SpecificError: log; raise` |
| **Validation** | Auto-correct input | `raise ValueError` immediately |
| **Return Values** | `None` or `False` on error | Raise explicit exception |

**Examples**:
```python
# ❌ BAD - Silent failures
def load_config(path):
    try:
        return yaml.safe_load(open(path))
    except:
        return {}  # Silent failure!

# ✅ GOOD - Fail fast with context
def load_config(path: Path) -> dict:
    """Load configuration from YAML file.
    
    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config is malformed
    """
    try:
        with open(path) as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error(f"Config file not found: {path}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML in {path}: {e}", exc_info=True)
        raise
```

## Critical Development Patterns

### 1. Event Flow Architecture
```
InputAdapter → input_queue (PriorityQueue) → Brain.process_event() → List[OutputEvent] → EventRouter → OutputAdapters
```

**Key Rule**: Brain NEVER knows about adapters/hardware - only `Event` objects. See [docs/EVENT_SYSTEM.md](docs/EVENT_SYSTEM.md) for complete event catalog.

### 2. DIRECT_OUTPUT Pattern (Hardware Testing)
Bypass Brain for testing output adapters without LLM:
```python
# Wrapper input event containing an output event
direct_event = Event(
    type=InputEventType.DIRECT_OUTPUT,
    content=inner_output_event,  # e.g., LED_CONTROL event
    priority=EventPriority.HIGH
)
```
See [docs/DIRECT_OUTPUT_PATTERN.md](docs/DIRECT_OUTPUT_PATTERN.md) for implementation details.

### 3. Configuration System
- **Environment**: `BUDDY_HOME` (project root) and `BUDDY_CONFIG` (YAML path) must be set
- **[config/config_loader.py](config/config_loader.py)**: `ConfigLoader.from_env()` validates environment and loads YAML
- **Config files**: [config/dev.yaml](config/dev.yaml) (mock adapters), [config/prod.yaml](config/prod.yaml) (real hardware)
- **Path resolution**: Relative paths in YAML resolve to `BUDDY_HOME`

### 4. Adapter Registration Pattern
```python
# Input adapters push events to shared queue
factory.create_input_adapter(class_name, config, input_queue)

# Output adapters register with router for specific event types
output_adapter = factory.create_output_adapter(class_name, config)
router.register_route(OutputEventType.SPEAK, output_adapter, "voice_out")
```

### 5. IPC via Named Pipes
- **[chat.py](chat.py)**: Interactive CLI sending events to Buddy via pipe (`data/buddy.in`)
- **[adapters/input/pipe_input.py](adapters/input/pipe_input.py)**: Reads JSON events from pipe
- **Commands**: `s <text>` (speak), `t <text>` (user speech), `lon` (LED on), `lb <n>` (LED blink)
- See [docs/PIPE_IPC.md](docs/PIPE_IPC.md) for protocol details

## Development Workflows

### Running Buddy
```bash
# Setup environment (first time)
bash scripts/setup_buddy.sh

# Run with dev config (mocks)
bash scripts/run_buddy.sh
# or directly:
export BUDDY_HOME=/path/to/cllmhl-buddy
export BUDDY_CONFIG=config/dev.yaml
python main.py
```

### Testing
```bash
# Unit tests (pytest)
pytest tests/test_core.py
pytest tests/test_adapters.py

# Integration tests
pytest tests/test_integration.py

# Hardware tests (requires actual hardware)
python tests/hardware/run_led_test.py
python tests/hardware/run_radar_test.py
```

### Hardware Testing Pattern
Hardware tests use DIRECT_OUTPUT to test output adapters standalone:
1. Load hardware-specific config (e.g., `tests/hardware/config/led_test.yaml`)
2. Create DIRECT_OUTPUT wrapper events
3. Send to input_queue
4. Observe physical output

Example: [tests/hardware/run_led_test.py](tests/hardware/run_led_test.py)

### Sending Commands (IPC)
```bash
# Start interactive CLI
python chat.py

# Or send single command
echo '{"type":"user_speech","content":"hello","priority":"high"}' > data/buddy.in
```

## Project-Specific Conventions

### Event Metadata Usage
- **LED_CONTROL**: `metadata={'led': 'ascolto', 'command': 'blink', 'times': 3}`
- **SENSOR_PRESENCE**: `metadata={'distance': 150, 'mov_energy': 45, 'static_energy': 20}`
- **SENSOR_TEMPERATURE**: `metadata={'temperature': 22.5, 'humidity': 65.0, 'temp_changed': True}`

### Memory System (RAG)
- **SQLite**: Conversation history in `data/system.db` (see [infrastructure/memory_store.py](infrastructure/memory_store.py))
- **ChromaDB**: Permanent facts in `data/memory/` (vector store for semantic search)
- **Archivist**: Periodically distills conversations into facts using LLM (interval configurable in YAML)

### Logging
- Rotating file handler configured in `main.py` (default: `logs/buddy_system.log`)
- Use emojis for visual parsing: `✅` (success), `❌` (error), `🧠` (brain), `📍` (router), `🔌` (adapter)

### Service Deployment (Raspberry Pi)
```bash
sudo bash scripts/install_service.sh
sudo systemctl start buddy
sudo journalctl -u buddy -f  # Follow logs
```
See [docs/SETUP_SERVICE.md](docs/SETUP_SERVICE.md)

## Key Files for Understanding System

| File | Purpose |
|------|---------|
| [main.py](main.py) | Main orchestration loop |
| [core/events.py](core/events.py) | Event type definitions |
| [docs/EVENT_SYSTEM.md](docs/EVENT_SYSTEM.md) | Complete event catalog with examples |
| [docs/DIRECT_OUTPUT_PATTERN.md](docs/DIRECT_OUTPUT_PATTERN.md) | Hardware testing pattern |
| [adapters/factory.py](adapters/factory.py) | Dynamic adapter creation |
| [config/dev.yaml](config/dev.yaml) | Development configuration example |

## Anti-Patterns to Avoid
- ❌ Never import hardware libraries in `core/` - keep business logic pure
- ❌ Don't create adapters without extending proper Port class (`InputPort`/`OutputPort`)
- ❌ Don't bypass event system - all communication must use events
- ❌ Don't hardcode paths - use `BUDDY_HOME` environment variable
- ❌ Don't use blocking I/O in adapters - use threads/async for long-running operations

## Quick Reference: Adding New Components

### New Input Adapter
1. Extend appropriate port class in [adapters/ports.py](adapters/ports.py) (e.g., `SensorInputPort`)
2. Implement `start()` and `stop()` methods
3. Create events with `create_input_event()` and push to `self.input_queue`
4. Add to [adapters/input/\_\_init\_\_.py](adapters/input/__init__.py) `__all__` list
5. Configure in YAML under `adapters.input`

### New Output Adapter
1. Extend `OutputPort` in [adapters/ports.py](adapters/ports.py)
2. Implement `send_event(event: Event)` method
3. Add to [adapters/output/\_\_init\_\_.py](adapters/output/__init__.py) `__all__` list
4. Configure in YAML under `adapters.output`
5. Router auto-registers based on config `event_types` list

### New Event Type
1. Add to `InputEventType` or `OutputEventType` enum in [core/events.py](core/events.py)
2. Document in [docs/EVENT_SYSTEM.md](docs/EVENT_SYSTEM.md) with content/metadata structure
3. Handle in `Brain.process_event()` if input event
4. Create output adapter to consume if output event
