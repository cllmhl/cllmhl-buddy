"""
Port Interfaces - Contratti per adapter Input/Output
Implementazione del Port Pattern per l'architettura esagonale.
"""

from abc import ABC, abstractmethod
from queue import PriorityQueue
from typing import Optional
import logging

# Import required - fail fast if not available
from core.events import OutputChannel, EventType

logger = logging.getLogger(__name__)


class InputPort(ABC):
    """
    Interfaccia BASE per adapter di INPUT (Primary Adapters).
    
    Gli input adapter:
    - Ricevono eventi dal mondo esterno (utente, sensori, etc)
    - Li trasformano in Event standardizzati
    - Li pubblicano sulla input_queue
    
    NON usare direttamente, estendere le Port specifiche:
    - VoiceInputPort per input vocale (wake word + speech)
    - SensorInputPort per sensori generici
    """
    
    def __init__(self, name: str, config: dict):
        """
        Args:
            name: Nome identificativo dell'adapter
            config: Configurazione specifica dell'adapter
        """
        self.name = name
        self.config = config
        self.running = False
        self.input_queue: Optional[PriorityQueue] = None
        logger.info(f"🔌 InputPort '{name}' initialized")
    
    @abstractmethod
    def start(self, input_queue: PriorityQueue) -> None:
        """
        Avvia l'adapter.
        
        Args:
            input_queue: Coda dove pubblicare gli eventi catturati
        """
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """Ferma l'adapter in modo pulito"""
        pass
    
    def is_running(self) -> bool:
        """Controlla se l'adapter è attivo"""
        return self.running


# ===== SPECIALIZED INPUT PORTS =====

class VoiceInputPort(InputPort):
    """
    Port per input VOCALE (wake word + speech recognition).
    """
    
    @classmethod
    def emitted_events(cls):
        """Eventi emessi da questa Port"""
        return [EventType.USER_SPEECH]


class SensorInputPort(InputPort):
    """
    Port BASE per sensori generici.
    Le sottoclassi devono specificare quali eventi emettono.
    """
    pass


class RadarInputPort(SensorInputPort):
    """
    Port per sensore RADAR (presenza/movimento).
    """
    
    @classmethod
    def emitted_events(cls):
        """Eventi emessi da questa Port"""
        return [EventType.SENSOR_PRESENCE, EventType.SENSOR_MOVEMENT]


class TemperatureInputPort(SensorInputPort):
    """
    Port per sensore TEMPERATURA/UMIDITÀ.
    """
    
    @classmethod
    def emitted_events(cls):
        """Eventi emessi da questa Port"""
        return [EventType.SENSOR_TEMPERATURE, EventType.SENSOR_HUMIDITY]


class OutputPort(ABC):
    """
    Interfaccia BASE per adapter di OUTPUT (Secondary Adapters).
    
    Gli output adapter:
    - Consumano eventi dalla loro coda dedicata
    - Eseguono azioni nel mondo esterno (parlare, LED, DB, etc)
    
    NON usare direttamente, estendere le Port specifiche:
    - VoiceOutputPort per output vocale/audio
    - LEDOutputPort per LED e segnalazioni visive
    - DatabaseOutputPort per persistenza dati
    """
    
    def __init__(self, name: str, config: dict):
        """
        Args:
            name: Nome identificativo dell'adapter
            config: Configurazione specifica dell'adapter
        """
        self.name = name
        self.config = config
        self.running = False
        self.output_queue: Optional[PriorityQueue] = None
        logger.info(f"🔌 OutputPort '{name}' initialized")
    
    @abstractmethod
    def start(self, output_queue: PriorityQueue) -> None:
        """
        Avvia l'adapter.
        
        Args:
            output_queue: Coda da cui consumare gli eventi
        """
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """Ferma l'adapter in modo pulito"""
        pass
    
    def is_running(self) -> bool:
        """Controlla se l'adapter è attivo"""
        return self.running


# ===== SPECIALIZED OUTPUT PORTS =====

class VoiceOutputPort(OutputPort):
    """
    Port per output VOCALE (TTS, audio).
    """
    
    @property
    def channel_type(self):
        """Tipo di canale: VOICE"""
        return OutputChannel.VOICE
    
    @classmethod
    def handled_events(cls):
        """Eventi gestiti da questa Port"""
        return [EventType.SPEAK]


class LEDOutputPort(OutputPort):
    """
    Port per output LED (segnalazioni visive).
    """
    
    @property
    def channel_type(self):
        """Tipo di canale: LED"""
        return OutputChannel.LED
    
    @classmethod
    def handled_events(cls):
        """Eventi gestiti da questa Port"""
        return [EventType.LED_ON, EventType.LED_OFF, EventType.LED_BLINK]


class DatabaseOutputPort(OutputPort):
    """
    Port per output DATABASE (persistenza).
    """
    
    @property
    def channel_type(self):
        """Tipo di canale: DATABASE"""
        return OutputChannel.DATABASE
    
    @classmethod
    def handled_events(cls):
        """Eventi gestiti da questa Port"""
        return [EventType.SAVE_HISTORY, EventType.SAVE_MEMORY]


class AudioDevicePort(ABC):
    """
    Port speciale per device audio condivisi (es: Jabra).
    
    Gestisce l'accesso esclusivo a device che sono sia input che output.
    Implementa il coordinamento per evitare conflitti.
    """
    
    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config
        self.device_available = True
        logger.info(f"🎤 AudioDevicePort '{name}' initialized")
    
    @abstractmethod
    def acquire_for_input(self) -> bool:
        """
        Richiede accesso al device per input (microfono).
        
        Returns:
            True se il device è disponibile, False altrimenti
        """
        pass
    
    @abstractmethod
    def acquire_for_output(self) -> bool:
        """
        Richiede accesso al device per output (speaker).
        
        Returns:
            True se il device è disponibile, False altrimenti
        """
        pass
    
    @abstractmethod
    def release(self) -> None:
        """Rilascia il device"""
        pass
