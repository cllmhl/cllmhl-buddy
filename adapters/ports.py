from __future__ import annotations

"""
Port Interfaces - Contratti per adapter Input/Output
Implementazione del Port Pattern per l'architettura esagonale.
"""

from abc import ABC, abstractmethod
from queue import PriorityQueue
from typing import List, Set, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from core.events import InputEventType, OutputEventType
    from core.commands import AdapterCommand

# Import required - fail fast if not available

logger = logging.getLogger(__name__)


class AdapterPort(ABC):
    """
    Classe base COMUNE per tutti gli adapter (Input e Output).
    
    Fornisce:
    - Gestione stato (name, config, running)
    - Lifecycle methods (start, stop, is_running)
    - Command handling (supported_commands, handle_command)
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
        logger.info(f"🔌 {self.__class__.__name__} '{name}' initialized")
    
    @abstractmethod
    def start(self) -> None:
        """Avvia l'adapter"""
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """Ferma l'adapter in modo pulito"""
        pass
    
    def is_running(self) -> bool:
        """Controlla se l'adapter è attivo"""
        return self.running
    
    def supported_commands(self) -> Set[AdapterCommand]:
        """
        Dichiara quali comandi questo adapter è in grado di gestire.
        Default: nessun comando (adapter senza controllo esterno).
        
        Returns:
            Set di AdapterCommand supportati
        """
        return set()
    
    def handle_command(self, command: AdapterCommand) -> bool:
        """
        Gestisce un comando dal Brain.
        Invocato SINCRONAMENTE dall'orchestrator per tutti gli adapter.
        
        Args:
            command: Comando da eseguire
            
        Returns:
            True se il comando è stato gestito, False se ignorato
        """
        return False  # Default: ignora tutti i comandi


class InputPort(AdapterPort):
    """
    Interfaccia per adapter di INPUT (Primary Adapters).
    
    Gli input adapter:
    - Ricevono eventi dal mondo esterno (utente, sensori, etc)
    - Li trasformano in Event standardizzati
    - Li pubblicano sulla input_queue
    """
    
    def __init__(self, name: str, config: dict, input_queue: PriorityQueue):
        """
        Args:
            name: Nome identificativo dell'adapter
            config: Configurazione specifica dell'adapter
            input_queue: Coda centralizzata dove pubblicare gli eventi
        """
        super().__init__(name, config)
        self.input_queue = input_queue


class OutputPort(AdapterPort):
    """
    Interfaccia per adapter di OUTPUT (Secondary Adapters).
    
    Gli output adapter:
    - Hanno una coda interna per ricevere eventi
    - Consumano eventi dalla loro coda interna
    - Eseguono azioni nel mondo esterno (parlare, LED, DB, etc)
    """
    
    def __init__(self, name: str, config: dict, queue_maxsize: int = 50):
        """
        Args:
            name: Nome identificativo dell'adapter
            config: Configurazione specifica dell'adapter
            queue_maxsize: Dimensione massima della coda interna
        """
        super().__init__(name, config)
        self.output_queue: PriorityQueue = PriorityQueue(maxsize=queue_maxsize)
        logger.info(f"  Queue size: {queue_maxsize}")
    
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
    
    @classmethod
    @abstractmethod
    def handled_events(cls) -> List[OutputEventType]:
        """
        Restituisce la lista di OutputEventType gestiti da questa Port.
        
        DEVE essere implementato da tutte le sottoclassi per dichiarare
        quali tipi di eventi sono in grado di processare.
        
        Returns:
            List[OutputEventType]: Eventi gestiti
        """
        pass
