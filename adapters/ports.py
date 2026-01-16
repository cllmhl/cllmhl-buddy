"""
Port Interfaces - Contratti per adapter Input/Output
Implementazione del Port Pattern per l'architettura esagonale.
"""

from abc import ABC, abstractmethod
from queue import PriorityQueue
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class InputPort(ABC):
    """
    Interfaccia per adapter di INPUT (Primary Adapters).
    
    Gli input adapter:
    - Ricevono eventi dal mondo esterno (utente, sensori, etc)
    - Li trasformano in Event standardizzati
    - Li pubblicano sulla input_queue
    
    Esempi: VoiceInput, SensorInput
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


class OutputPort(ABC):
    """
    Interfaccia per adapter di OUTPUT (Secondary Adapters).
    
    Gli output adapter:
    - Consumano eventi dalla loro coda dedicata
    - Eseguono azioni nel mondo esterno (parlare, LED, DB, etc)
    
    Esempi: VoiceOutput, LEDOutput, DatabaseOutput
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
