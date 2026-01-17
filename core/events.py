"""
Event System - Definizioni eventi e priorità
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Optional
import time


class OutputChannel(Enum):
    """
    Canali di output del sistema.
    Questi devono corrispondere ai nomi degli adapter nella configurazione YAML.
    """
    VOICE = "voice"          # Output vocale (TTS)
    LED = "led"              # LED di stato/segnalazione
    DATABASE = "database"    # Persistenza dati
    ARCHIVIST = "archivist"  # Distillazione memoria
    CONSOLE = "console"      # Output console/debug


class EventType(Enum):
    """Tipi di eventi nel sistema"""
    
    # ===== INPUT EVENTS =====
    USER_SPEECH = "user_speech"           # Input vocale utente
    
    # Sensori
    SENSOR_PRESENCE = "sensor_presence"   # Radar presenza
    SENSOR_TEMPERATURE = "sensor_temperature"
    SENSOR_HUMIDITY = "sensor_humidity"
    SENSOR_MOVEMENT = "sensor_movement"
    
    # ===== OUTPUT EVENTS =====
    SPEAK = "speak"                       # Emetti audio vocale
    
    # LED
    LED_ON = "led_on"
    LED_OFF = "led_off"
    LED_BLINK = "led_blink"
    
    # Storage
    SAVE_HISTORY = "save_history"         # Salva in history DB
    SAVE_MEMORY = "save_memory"           # Salva in memoria permanente
    DISTILL_MEMORY = "distill_memory"     # Avvia distillazione memoria (Archivist)
    
    # Sistema
    SHUTDOWN = "shutdown"
    RESTART = "restart"


# ===== EVENT ROUTING MAP =====
# Il routing è ora DINAMICO: viene costruito interrogando gli adapter configurati
# tramite i loro metodi handled_events() e channel_type


def build_event_routing_from_adapters(output_adapters: list) -> dict[EventType, OutputChannel]:
    """
    Costruisce dinamicamente il mapping EventType -> OutputChannel
    interrogando gli adapter OUTPUT effettivamente configurati.
    
    Args:
        output_adapters: Lista di adapter output configurati
    
    Returns:
        Dict con mapping EventType -> OutputChannel
        
    Example:
        >>> adapters = [voice_adapter, led_adapter, db_adapter]
        >>> routing = build_event_routing_from_adapters(adapters)
        >>> routing[EventType.SPEAK]  # OutputChannel.VOICE
    """
    mapping = {}
    
    for adapter in output_adapters:
        channel = adapter.channel_type
        # Ottieni gli eventi gestiti dalla classe Port dell'adapter
        handled = adapter.__class__.handled_events()
        
        for event_type in handled:
            if event_type in mapping:
                # Log warning se due adapter gestiscono lo stesso evento
                # (potrebbe essere intenzionale per broadcast)
                pass
            mapping[event_type] = channel
    
    return mapping


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
    type: EventType = field(compare=False)
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
    event_type: EventType,
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
    event_type: EventType,
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
