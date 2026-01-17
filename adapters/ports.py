"""
Port Interfaces - Contratti per adapter Input/Output
Implementazione del Port Pattern per l'architettura esagonale.
"""

from abc import ABC, abstractmethod
from queue import PriorityQueue
from typing import Optional
import logging

# Import required - fail fast if not available
from core.events import InputEventType, OutputEventType

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
    
    def __init__(self, name: str, config: dict, input_queue: PriorityQueue):
        """
        Args:
            name: Nome identificativo dell'adapter
            config: Configurazione specifica dell'adapter
            input_queue: Coda centralizzata dove pubblicare gli eventi
        """
        self.name = name
        self.config = config
        self.running = False
        self.input_queue = input_queue
        logger.info(f"🔌 InputPort '{name}' initialized")
    
    @abstractmethod
    def start(self) -> None:
        """
        Avvia l'adapter.
        L'adapter usa self.input_queue per pubblicare eventi.
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
        return [InputEventType.USER_SPEECH]


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
        return [InputEventType.SENSOR_PRESENCE, InputEventType.SENSOR_MOVEMENT]


class TemperatureInputPort(SensorInputPort):
    """
    Port per sensore TEMPERATURA/UMIDITÀ.
    """
    
    @classmethod
    def emitted_events(cls):
        """Eventi emessi da questa Port"""
        return [InputEventType.SENSOR_TEMPERATURE, InputEventType.SENSOR_HUMIDITY]


class OutputPort(ABC):
    """
    Interfaccia BASE per adapter di OUTPUT (Secondary Adapters).
    
    Gli output adapter:
    - Hanno una coda interna per ricevere eventi
    - Consumano eventi dalla loro coda interna
    - Eseguono azioni nel mondo esterno (parlare, LED, DB, etc)
    
    NON usare direttamente, estendere le Port specifiche:
    - VoiceOutputPort per output vocale/audio
    - LEDOutputPort per LED e segnalazioni visive
    - DatabaseOutputPort per persistenza dati
    """
    
    def __init__(self, name: str, config: dict, queue_maxsize: int = 50):
        """
        Args:
            name: Nome identificativo dell'adapter
            config: Configurazione specifica dell'adapter
            queue_maxsize: Dimensione massima della coda interna
        """
        self.name = name
        self.config = config
        self.running = False
        # Coda interna dell'adapter
        self.output_queue = PriorityQueue(maxsize=queue_maxsize)
        logger.info(f"🔌 OutputPort '{name}' initialized (queue_size={queue_maxsize})")
    
    def send_event(self, event) -> bool:
        """
        Invia un evento all'adapter (chiamato dal Router).
        
        Args:
            event: Evento da processare
            
        Returns:
            True se l'evento è stato accodato, False se la coda è piena
        """
        try:
            self.output_queue.put(event, block=False)
            return True
        except Exception:
            logger.error(f"❌ Queue FULL for {self.name}! Event dropped: {event}")
            return False
    
    @abstractmethod
    def start(self) -> None:
        """
        Avvia l'adapter.
        L'adapter deve avviare il suo worker thread che consuma dalla coda interna.
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
    
    @classmethod
    def handled_events(cls):
        """Eventi gestiti da questa Port"""
        return [OutputEventType.SPEAK]


class LEDOutputPort(OutputPort):
    """
    Port per output LED (segnalazioni visive).
    """
    
    @classmethod
    def handled_events(cls):
        """Eventi gestiti da questa Port"""
        return [OutputEventType.LED_ON, OutputEventType.LED_OFF, OutputEventType.LED_BLINK]


class DatabaseOutputPort(OutputPort):
    """
    Port per output DATABASE (persistenza).
    """
    
    @classmethod
    def handled_events(cls):
        """Eventi gestiti da questa Port"""
        return [OutputEventType.SAVE_HISTORY, OutputEventType.SAVE_MEMORY]


class ArchivistOutputPort(OutputPort):
    """
    Port per output ARCHIVIST (distillazione memoria).
    """
    
    @classmethod
    def handled_events(cls):
        """Eventi gestiti da questa Port"""
        return [OutputEventType.DISTILL_MEMORY]


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
