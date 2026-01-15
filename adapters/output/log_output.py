"""
Log Output Adapter - Gestione Logging
"""

import logging
import threading
from queue import PriorityQueue, Empty

from adapters.ports import OutputPort
from core.events import Event, EventType

logger = logging.getLogger(__name__)


class LogOutput(OutputPort):
    """
    Log Output Adapter.
    Gestisce tutti gli eventi di logging e li scrive nel logger Python.
    """
    
    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        
        self.worker_thread = None
        
        # Logger dedicato per output
        self.output_logger = logging.getLogger("buddy.output")
        
        logger.info(f"📝 LogOutput initialized")
    
    def start(self, output_queue: PriorityQueue) -> None:
        """Avvia worker"""
        self.output_queue = output_queue
        self.running = True
        
        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name=f"{self.name}_worker"
        )
        self.worker_thread.start()
        
        logger.info(f"▶️  {self.name} started")
    
    def stop(self) -> None:
        """Ferma worker"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=2.0)
        
        logger.info(f"⏹️  {self.name} stopped")
    
    def _worker_loop(self) -> None:
        """Loop principale"""
        while self.running:
            try:
                event = self.output_queue.get(timeout=0.5)
                
                # Gestisce tutti i tipi di log
                if event.type == EventType.LOG_DEBUG:
                    self.output_logger.debug(str(event.content))
                elif event.type == EventType.LOG_INFO:
                    self.output_logger.info(str(event.content))
                elif event.type == EventType.LOG_WARNING:
                    self.output_logger.warning(str(event.content))
                elif event.type == EventType.LOG_ERROR:
                    self.output_logger.error(str(event.content))
                
                self.output_queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error in log worker: {e}")
