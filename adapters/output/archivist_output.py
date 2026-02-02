"""
Archivist Output Adapter - Distillazione della memoria
"""

import logging
import threading
from queue import PriorityQueue, Empty
from typing import Optional

from core.events import OutputEvent, OutputEventType
from adapters.ports import OutputPort
from core.archivist import BuddyArchivist
import os

logger = logging.getLogger(__name__)


class ArchivistOutput(OutputPort):
    """
    Archivist Output Adapter.
    Distilla conversazioni in memoria permanente usando Gemini.
    """
    
    def __init__(self, name: str, config: dict):
        queue_maxsize = config['queue_maxsize']
        super().__init__(name, config, queue_maxsize)
        
        # Inizializza Archivist (singleton)
        self.archivist = BuddyArchivist.get_instance()
        
        self.worker_thread: Optional[threading.Thread] = None
    
    @classmethod
    def handled_events(cls):
        """Eventi gestiti da questo adapter"""
        return [OutputEventType.DISTILL_MEMORY]
    
    def start(self) -> None:
        """Avvia worker che consuma dalla coda interna"""
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
        logger.info(f"⏸️  Stopping {self.name}...")
        self.running = False
        
        # Aspetta thread con timeout
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=3.0)
            if self.worker_thread.is_alive():
                logger.warning(f"⚠️  {self.name} thread did not terminate")
        
        logger.info(f"⏹️  {self.name} stopped")
    
    def _worker_loop(self) -> None:
        """Loop principale"""
        while self.running:
            try:
                event = self.output_queue.get(timeout=0.5)
                
                if event.type == OutputEventType.DISTILL_MEMORY:
                    self._handle_distill_memory(event)
                
                self.output_queue.task_done()
                
            except Empty:
                continue
            except KeyboardInterrupt:
                logger.info("Archivist worker interrupted")
                break
            except Exception as e:
                logger.error(
                    f"Error in archivist worker: {e}",
                    exc_info=True
                )
    
    def _handle_distill_memory(self, event: OutputEvent) -> None:
        """Esegue distillazione della memoria"""
        
        try:
            logger.info("📚 Handling memory distillation")
            
            # Esegui distillazione
            self.archivist.distill_and_save()
            
            logger.info(f"✅ Memory distillation completed")
            
        except Exception as e:
            logger.error(f"❌ Error during memory distillation: {e}", exc_info=True)


