"""
Database Output Adapter - Gestione persistenza
"""

import logging
import threading
from queue import PriorityQueue, Empty

from adapters.ports import OutputPort
from core.events import Event, EventType
from database_buddy import BuddyDatabase

logger = logging.getLogger(__name__)


class DatabaseOutput(OutputPort):
    """
    Database Output Adapter.
    Gestisce salvataggio history e memoria permanente.
    """
    
    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        
        # Configurazione database
        sqlite_path = config.get('sqlite_path', 'buddy_system.db')
        chroma_path = config.get('chroma_path', './buddy_memory')
        
        # Inizializza database
        try:
            self.db = BuddyDatabase(db_name=sqlite_path, chroma_path=chroma_path)
            logger.info(f"✅ Database initialized (SQLite: {sqlite_path}, Chroma: {chroma_path})")
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            self.db = None
        
        self.worker_thread = None
    
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
        """Ferma worker e chiude database"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=2.0)
        
        if self.db:
            self.db.close()
        
        logger.info(f"⏹️  {self.name} stopped")
    
    def _worker_loop(self) -> None:
        """Loop principale"""
        while self.running:
            try:
                event = self.output_queue.get(timeout=0.5)
                
                if event.type == EventType.SAVE_HISTORY:
                    self._handle_save_history(event)
                elif event.type == EventType.SAVE_MEMORY:
                    self._handle_save_memory(event)
                
                self.output_queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error in database worker: {e}", exc_info=True)
    
    def _handle_save_history(self, event: Event) -> None:
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
    
    def _handle_save_memory(self, event: Event) -> None:
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
