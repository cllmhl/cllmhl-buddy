"""
Keyboard Input Adapter - Input da tastiera (stdin)
"""

import sys
import logging
import threading
from queue import PriorityQueue

from adapters.ports import InputPort
from core.events import create_input_event, EventType, EventPriority

logger = logging.getLogger(__name__)


class KeyboardInput(InputPort):
    """
    Keyboard Input Adapter.
    Legge input da stdin (tastiera).
    """
    
    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        self.worker_thread = None
        logger.info(f"⌨️  KeyboardInput initialized")
    
    def start(self, input_queue: PriorityQueue) -> None:
        """Avvia worker thread"""
        self.input_queue = input_queue
        self.running = True
        
        # Verifica se stdin è interattivo
        if not sys.stdin.isatty():
            logger.warning("⚠️ stdin is not interactive, keyboard input disabled")
            return
        
        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name=f"{self.name}_worker"
        )
        self.worker_thread.start()
        
        logger.info(f"▶️  {self.name} started")
        print("Tu > ", end="", flush=True)
    
    def stop(self) -> None:
        """Ferma worker"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=1.0)
        
        logger.info(f"⏹️  {self.name} stopped")
    
    def _worker_loop(self) -> None:
        """Loop principale di lettura tastiera"""
        while self.running:
            try:
                text = input()
                
                if text:
                    # Crea evento
                    event = create_input_event(
                        EventType.KEYBOARD_INPUT,
                        text,
                        source="keyboard",
                        priority=EventPriority.HIGH
                    )
                    
                    self.input_queue.put(event)
                    logger.debug(f"⌨️  Keyboard input: {text}")
                    
                    # Mostra prompt
                    print("Tu > ", end="", flush=True)
            
            except EOFError:
                logger.info("EOF received, keyboard input terminating")
                break
            except Exception as e:
                logger.error(f"Error reading keyboard input: {e}")
                break
