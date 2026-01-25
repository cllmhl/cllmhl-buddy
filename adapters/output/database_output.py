"""
Database Output Adapter - Gestione persistenza
"""

import logging
import threading
from queue import PriorityQueue, Empty
from typing import Optional

from adapters.ports import OutputPort
from core.events import OutputEvent, OutputEventType
from infrastructure.memory_store import MemoryStore

logger = logging.getLogger(__name__)


class DatabaseOutput(OutputPort):
    """
    Database Output Adapter.
    Gestisce salvataggio history e memoria permanente.
    """
    
    def __init__(self, name: str, config: dict):
        queue_maxsize = config['queue_maxsize']  # Fail-fast: must be present
        super().__init__(name, config, queue_maxsize)
        
        # Configurazione database
        sqlite_path = config['sqlite_path']
        chroma_path = config['chroma_path']
        
        # Inizializza database
        self.db: Optional[MemoryStore]
        try:
            self.db = MemoryStore(db_name=sqlite_path, chroma_path=chroma_path)
            logger.info(f"✅ Database initialized (SQLite: {sqlite_path}, Chroma: {chroma_path})")
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            self.db = None
        
        self.worker_thread: Optional[threading.Thread] = None
    
    @classmethod
    def handled_events(cls):
        """Eventi gestiti da questo adapter"""
        return [OutputEventType.SAVE_HISTORY, OutputEventType.SAVE_MEMORY]
    
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
        """Ferma worker e chiude database"""
        logger.info(f"⏸️  Stopping {self.name}...")
        self.running = False
        
        # Aspetta thread con timeout
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=3.0)
            if self.worker_thread.is_alive():
                logger.warning(f"⚠️  {self.name} thread did not terminate")
        
        # Cleanup database
        if self.db:
            try:
                self.db.close()
                logger.debug("Database closed")
            except Exception as e:
                logger.debug(f"Database close error: {e}")
        
        logger.info(f"⏹️  {self.name} stopped")
    
    def _worker_loop(self) -> None:
        """Loop principale"""
        while self.running:
            try:
                event = self.output_queue.get(timeout=0.5)
                
                if event.type == OutputEventType.SAVE_HISTORY:
                    self._handle_save_history(event)
                elif event.type == OutputEventType.SAVE_MEMORY:
                    self._handle_save_memory(event)
                
                self.output_queue.task_done()
                
            except Empty:
                continue
            except KeyboardInterrupt:
                logger.info("Database worker interrupted")
                break
            except Exception as e:
                logger.error(
                    f"Error in database worker: {e}",
                    exc_info=True  # Full stack trace
                )
    
    def _handle_save_history(self, event: OutputEvent) -> None:
        """Salva in history (conversazione temporanea)"""
        if not self.db:
            logger.warning("Database not available, skipping save_history")
            return
        
        try:
            # event.content deve essere dict con 'role' e 'text'
            data = event.content
            if isinstance(data, dict) and 'role' in data and 'text' in data:
                self.db.add_history(data['role'], data['text'])
                logger.debug(f"💾 History saved: {data['role']}")
            else:
                logger.warning(f"Invalid history data format: {data}")
        
        except Exception as e:
            logger.error(f"Error saving history: {e}")
    
    def _handle_save_memory(self, event: OutputEvent) -> None:
        """Salva in memoria permanente (ChromaDB)"""
        if not self.db:
            logger.warning("Database not available, skipping save_memory")
            return
        
        try:
            # event.content deve essere dict con 'fact', 'category', 'notes', 'importance'
            data = event.content
            if isinstance(data, dict):
                fact = data.get('fact', '')
                category = data.get('category', 'generale')
                notes = data.get('notes', '')
                importance = data.get('importance', 1)
                
                self.db.add_permanent_memory(fact, category, notes, importance)
                logger.debug(f"🧠 Memory saved: {fact[:50]}...")
            else:
                logger.warning(f"Invalid memory data format: {data}")
        
        except Exception as e:
            logger.error(f"Error saving memory: {e}")


