"""
Event System - Definizioni eventi e priorità
Architettura Esagonale: separazione esplicita tra Input e Output events
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Optional, Union
import time


class InputEventType(Enum):
    """
    Eventi di Input - Generati da Input Adapters (Primary Ports).
    Rappresentano stimoli dal mondo esterno verso il core.
    """
    # Input vocale
    USER_SPEECH = "user_speech"           # Input vocale utente
    
    # Sensori
    SENSOR_PRESENCE = "sensor_presence"   # Radar presenza
    SENSOR_TEMPERATURE = "sensor_temperature"
    SENSOR_HUMIDITY = "sensor_humidity"
    SENSOR_MOVEMENT = "sensor_movement"
    
    # Bypass Brain - per test e comandi diretti
    DIRECT_OUTPUT = "direct_output"       # Wrapper che contiene un OutputEvent da inoltrare direttamente
    
    # Sistema
    SHUTDOWN = "shutdown"
    RESTART = "restart"


class OutputEventType(Enum):
    """
    Eventi di Output - Consumati da Output Adapters (Secondary Ports).
    Rappresentano azioni che il core richiede verso il mondo esterno.
    """
    # Audio
    SPEAK = "speak"                       # Emetti audio vocale
    
    # LED
    LED_ON = "led_on"
    LED_OFF = "led_off"
    LED_BLINK = "led_blink"
    
    # Storage
    SAVE_HISTORY = "save_history"         # Salva in history DB
    SAVE_MEMORY = "save_memory"           # Salva in memoria permanente
    DISTILL_MEMORY = "distill_memory"     # Avvia distillazione memoria (Archivist)


# Compatibility layer: EventType with all events accessible
class EventType:
    """
    Backward compatibility wrapper for tests and legacy code.
    Provides access to both Input and Output event types.
    """
    # Input events
    USER_SPEECH = InputEventType.USER_SPEECH
    SENSOR_PRESENCE = InputEventType.SENSOR_PRESENCE
    SENSOR_TEMPERATURE = InputEventType.SENSOR_TEMPERATURE
    SENSOR_HUMIDITY = InputEventType.SENSOR_HUMIDITY
    SENSOR_MOVEMENT = InputEventType.SENSOR_MOVEMENT
    DIRECT_OUTPUT = InputEventType.DIRECT_OUTPUT
    SHUTDOWN = InputEventType.SHUTDOWN
    RESTART = InputEventType.RESTART
    
    # Output events
    SPEAK = OutputEventType.SPEAK
    LED_ON = OutputEventType.LED_ON
    LED_OFF = OutputEventType.LED_OFF
    LED_BLINK = OutputEventType.LED_BLINK
    SAVE_HISTORY = OutputEventType.SAVE_HISTORY
    SAVE_MEMORY = OutputEventType.SAVE_MEMORY
    DISTILL_MEMORY = OutputEventType.DISTILL_MEMORY


class EventPriority(Enum):
    """
    Priorità eventi per PriorityQueue.
    Valore minore = priorità maggiore
    """
    CRITICAL = 0    # Emergenze (STOP, SHUTDOWN)
    HIGH = 1        # Comandi utente diretti
    NORMAL = 2      # Operazioni normali
    LOW = 3         # Background tasks (logging, archiving)
    
    def __lt__(self, other):
        return self.value < other.value


@dataclass(order=True)
class Event:
    """
    Evento base del sistema.
    Usato sia per input che output.
    """
    
    # Priority first per PriorityQueue sorting
    priority: EventPriority = field(compare=True)
    
    # Event data
    type: Union[InputEventType, OutputEventType] = field(compare=False)
    content: Any = field(compare=False)
    
    # Metadata
    timestamp: float = field(default_factory=time.time, compare=False)
    source: Optional[str] = field(default=None, compare=False)
    metadata: Optional[dict] = field(default=None, compare=False)
    
    def __repr__(self):
        content_str = str(self.content)[:50]
        if len(str(self.content)) > 50:
            content_str += "..."
        return (f"Event(type={self.type.value}, "
                f"priority={self.priority.name}, "
                f"content={content_str})")


# ===== HELPER FUNCTIONS =====

def create_input_event(
    event_type: InputEventType,
    content: Any,
    source: str,
    priority: EventPriority = EventPriority.NORMAL,
    metadata: Optional[dict] = None
) -> Event:
    """Helper per creare eventi di input"""
    return Event(
        priority=priority,
        type=event_type,
        content=content,
        source=source,
        metadata=metadata or {}
    )


def create_output_event(
    event_type: OutputEventType,
    content: Any,
    priority: EventPriority = EventPriority.NORMAL,
    metadata: Optional[dict] = None
) -> Event:
    """Helper per creare eventi di output"""
    return Event(
        priority=priority,
        type=event_type,
        content=content,
        metadata=metadata or {}
    )
