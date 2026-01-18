"""
Pipe Output Adapter - Scrive eventi su named pipe
Permette monitoraggio eventi di buddy tramite IPC
"""

import os
import json
import logging
import threading
from pathlib import Path
from queue import Empty
from typing import Optional, Set

from core.events import Event, OutputEventType
from adapters.ports import OutputPort


logger = logging.getLogger(__name__)


class PipeOutputAdapter(OutputPort):
    """
    Output adapter che scrive eventi su una named pipe (FIFO).
    Formato: JSON line-delimited
    
    Configurabile per filtrare quali tipi di eventi scrivere.
    Scrittura non-bloccante: se nessuno legge, gli eventi vengono scartati.
    
    Esempio JSON emesso:
    {
        "type": "speak",
        "content": "Hello!",
        "timestamp": 1234567890.123,
        "source": "brain",
        "metadata": {...}
    }
    """
    
    @classmethod
    def handled_events(cls):
        """Eventi gestiti da questa Port (tutti gli OutputEvent)"""
        return list(OutputEventType)
    
    def __init__(
        self, 
        name: str,
        config: dict,
        queue_maxsize: int = 50
    ):
        """
        Args:
            name: Nome adapter
            config: Configurazione con:
                - pipe_path: Path alla named pipe (default: data/buddy.out)
                - event_types: Lista di OutputEventType da monitorare (default: tutti)
                             Es: ["speak", "led_control"]
            queue_maxsize: Dimensione coda interna
        """
        super().__init__(name, config, queue_maxsize)
        self.pipe_path = Path(config['pipe_path'])
        self._worker_thread: Optional[threading.Thread] = None
        # Parse event types filter (fail-fast)
        if 'event_types' not in config:
            raise KeyError("Missing required config key: 'event_types' for PipeOutputAdapter")
        event_types = config['event_types']
        self.event_types: Set[OutputEventType] = set()
        for et in event_types:
            try:
                if isinstance(et, str):
                    self.event_types.add(OutputEventType[et.upper()])
                else:
                    self.event_types.add(et)
            except KeyError:
                logger.warning(f"Tipo evento sconosciuto: {et}")
        logger.info(f"PipeOutput filtro eventi: {[et.value for et in self.event_types]}")
        
    def start(self):
        """Avvia l'adapter"""
        if self.running:
            logger.warning("PipeOutput già in esecuzione")
            return
            
        # Crea directory se non esiste
        self.pipe_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Crea named pipe se non esiste
        if not self.pipe_path.exists():
            try:
                os.mkfifo(self.pipe_path)
                logger.info(f"Named pipe creata: {self.pipe_path}")
            except OSError as e:
                logger.error(f"Errore creazione named pipe: {e}")
                return
        elif not self._is_fifo(self.pipe_path):
            logger.error(f"{self.pipe_path} esiste ma non è una named pipe")
            return
            
        self.running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name=f"{self.name}_worker"
        )
        self._worker_thread.start()
        logger.info(f"PipeOutput avviato su {self.pipe_path}")
        
    def stop(self):
        """Ferma l'adapter"""
        if not self.running:
            return
        
        logger.info(f"⏸️  Stopping {self.name}...")
        self.running = False
        
        # Aspetta thread con timeout
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=3.0)
            if self._worker_thread.is_alive():
                logger.warning(f"⚠️  {self.name} thread did not terminate")
            
        logger.info(f"⏹️  {self.name} stopped")
        
    def _worker_loop(self):
        """Loop di consumazione eventi dalla coda interna"""
        while self.running:
            try:
                event = self.output_queue.get(timeout=0.5)
                self.handle_event(event)
                self.output_queue.task_done()
            except Empty:
                continue
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Errore worker loop: {e}", exc_info=True)
        
    def _is_fifo(self, path: Path) -> bool:
        """Verifica se il path è una named pipe"""
        import stat
        return stat.S_ISFIFO(os.stat(path).st_mode)
        
    def handle_event(self, event: Event):
        """
        Gestisce un evento scrivendolo sulla pipe.
        Filtra per event_types configurati.
        """
        if not self.running:
            return
            
        # Filtra per tipo
        if event.type not in self.event_types:
            return
            
        # Serializza evento
        event_data = {
            "type": event.type.value,
            "content": event.content,
            "timestamp": event.timestamp,
            "priority": event.priority.name,
            "source": event.source,
            "metadata": event.metadata or {}
        }
        
        json_line = json.dumps(event_data) + '\n'
        
        # Scrivi sulla pipe (non-bloccante)
        try:
            # Apri in write mode non-bloccante
            fd = os.open(self.pipe_path, os.O_WRONLY | os.O_NONBLOCK)
            try:
                os.write(fd, json_line.encode('utf-8'))
                logger.debug(f"Event scritto su pipe: {event.type.value}")
            finally:
                os.close(fd)
                
        except OSError as e:
            # ENXIO = nessuno sta leggendo dalla pipe
            if e.errno == 6:  # ENXIO
                logger.debug("Nessun reader sulla pipe, evento scartato")
            else:
                logger.error(f"Errore scrittura pipe: {e}")
