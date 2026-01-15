"""
Pipe Input Adapter - Input da Named Pipe (FIFO)
"""

import os
import logging
import threading
from queue import PriorityQueue

from adapters.ports import InputPort
from core.events import create_input_event, EventType, EventPriority

logger = logging.getLogger(__name__)


class PipeInput(InputPort):
    """
    Pipe Input Adapter.
    Legge comandi da Named Pipe (FIFO).
    """
    
    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        
        self.pipe_path = config.get('pipe_path', '/tmp/buddy_pipe')
        self.worker_thread = None
        
        # Crea pipe se non esiste
        self._create_pipe()
        
        logger.info(f"📡 PipeInput initialized (path: {self.pipe_path})")
    
    def _create_pipe(self) -> None:
        """Crea Named Pipe"""
        if os.path.exists(self.pipe_path):
            # Rimuovi pipe esistente
            try:
                os.unlink(self.pipe_path)
                logger.debug(f"Removed existing pipe: {self.pipe_path}")
            except Exception as e:
                logger.warning(f"Could not remove existing pipe: {e}")
        
        try:
            os.mkfifo(self.pipe_path)
            os.chmod(self.pipe_path, 0o666)
            logger.info(f"✅ Named pipe created: {self.pipe_path}")
        except Exception as e:
            logger.error(f"❌ Failed to create pipe: {e}")
            raise
    
    def start(self, input_queue: PriorityQueue) -> None:
        """Avvia worker thread"""
        self.input_queue = input_queue
        self.running = True
        
        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name=f"{self.name}_worker"
        )
        self.worker_thread.start()
        
        logger.info(f"▶️  {self.name} started (listening on {self.pipe_path})")
    
    def stop(self) -> None:
        """Ferma worker e rimuove pipe"""
        self.running = False
        
        if self.worker_thread:
            # Write dummy data to unblock pipe read
            try:
                with open(self.pipe_path, 'w') as pipe:
                    pipe.write("\n")
            except:
                pass
            
            self.worker_thread.join(timeout=2.0)
        
        # Cleanup pipe
        if os.path.exists(self.pipe_path):
            try:
                os.unlink(self.pipe_path)
                logger.debug(f"Removed pipe: {self.pipe_path}")
            except Exception as e:
                logger.warning(f"Could not remove pipe: {e}")
        
        logger.info(f"⏹️  {self.name} stopped")
    
    def _worker_loop(self) -> None:
        """Loop principale di lettura pipe"""
        logger.info(f"📡 Pipe listening on: {self.pipe_path}")
        
        while self.running:
            try:
                # Apri pipe in lettura (blocca finché qualcuno scrive)
                with open(self.pipe_path, 'r') as pipe:
                    for line in pipe:
                        if not self.running:
                            break
                        
                        text = line.strip()
                        if text:
                            logger.info(f"📡 Pipe command received: {text}")
                            
                            # Crea evento
                            event = create_input_event(
                                EventType.PIPE_COMMAND,
                                text,
                                source="pipe",
                                priority=EventPriority.HIGH
                            )
                            
                            self.input_queue.put(event)
            
            except Exception as e:
                if self.running:
                    logger.error(f"Error reading pipe: {e}")
                    # Wait before retry
                    threading.Event().wait(1.0)
