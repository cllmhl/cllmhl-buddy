"""
Archivist Output Adapter - Distillazione della memoria
"""

import logging
import threading
from queue import PriorityQueue, Empty
from typing import Optional

from core.events import Event, OutputEventType
from adapters.ports import ArchivistOutputPort
from infrastructure.memory_store import MemoryStore
from core.archivist import BuddyArchivist
import os

logger = logging.getLogger(__name__)


class ArchivistOutput(ArchivistOutputPort):
    """
    Archivist Output Adapter.
    Distilla conversazioni in memoria permanente usando Gemini.
    """
    
    def __init__(self, name: str, config: dict):
        queue_maxsize = config.get('queue_maxsize', 50)
        super().__init__(name, config, queue_maxsize)
        
        # Configurazione
        self.archivist_config = config.get('archivist_config', {})
        sqlite_path = config.get('sqlite_path', 'data/system.db')
        chroma_path = config.get('chroma_path', 'data/memory')
        
        # Inizializza database
        self.db: Optional[MemoryStore]
        try:
            self.db = MemoryStore(db_name=sqlite_path, chroma_path=chroma_path)
            logger.info(f"✅ Archivist database initialized")
        except Exception as e:
            logger.error(f"❌ Archivist database initialization failed: {e}")
            self.db = None
        
        # Inizializza Archivist
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found for Archivist")
        
        self.archivist: Optional[BuddyArchivist]
        try:
            self.archivist = BuddyArchivist(api_key, self.archivist_config)
            logger.info(f"✅ BuddyArchivist initialized (model: {self.archivist_config.get('model_id')})")
        except Exception as e:
            logger.error(f"❌ BuddyArchivist initialization failed: {e}")
            self.archivist = None
        
        self.worker_thread: Optional[threading.Thread] = None
    
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
    
    def _handle_distill_memory(self, event: Event) -> None:
        """Esegue distillazione della memoria"""
        if not self.db or not self.archivist:
            logger.warning("Archivist or database not available, skipping distillation")
            return
        
        try:
            # Controlla se ci sono conversazioni non processate
            unprocessed = self.db.get_unprocessed_history()
            
            if len(unprocessed) == 0:
                logger.debug("📚 No unprocessed history to distill")
                return
            
            logger.info(f"📚 Starting memory distillation ({len(unprocessed)} messages)")
            
            # Esegui distillazione
            self.archivist.distill_and_save(self.db)
            
            logger.info(f"✅ Memory distillation completed")
            
        except Exception as e:
            logger.error(f"❌ Error during memory distillation: {e}", exc_info=True)


class MockArchivistOutput(ArchivistOutputPort):
    """
    Mock Archivist Output per testing.
    Simula distillazione senza effettivamente processare.
    """
    
    def __init__(self, name: str, config: dict):
        queue_maxsize = config.get('queue_maxsize', 50)
        super().__init__(name, config, queue_maxsize)
        self.worker_thread: Optional[threading.Thread] = None
        logger.info(f"📚 MockArchivistOutput initialized")
    
    def start(self) -> None:
        """Avvia worker mock"""
        self.running = True
        
        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name=f"{self.name}_worker"
        )
        self.worker_thread.start()
        
        logger.info(f"▶️  {self.name} started (MOCK)")
    
    def stop(self) -> None:
        """Ferma worker"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=2.0)
        
        logger.info(f"⏹️  {self.name} stopped (MOCK)")
    
    def _worker_loop(self) -> None:
        """Loop principale mock"""
        while self.running:
            try:
                event = self.output_queue.get(timeout=0.5)
                
                if event.type == OutputEventType.DISTILL_MEMORY:
                    logger.info("📚 MOCK: Distillation triggered (no actual processing)")
                
                self.output_queue.task_done()
                
            except Empty:
                continue
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in mock archivist: {e}")
