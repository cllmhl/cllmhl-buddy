import logging
import threading
from queue import Empty
from typing import List

from adapters.ports import OutputPort
from core.events import OutputEvent, OutputEventType

logger = logging.getLogger(__name__)


class LogOutput(OutputPort):
    def __init__(self, name: str, config: dict, **kwargs):
        super().__init__(name, config, **kwargs)
        self._worker_thread = None
        self.running = False

    def start(self) -> None:
        self.running = True
        self._worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._worker_thread.start()
        logger.info(f"{self.name} started.")

    def stop(self) -> None:
        self.running = False
        if self._worker_thread:
            self._worker_thread.join()
        logger.info(f"{self.name} stopped.")

    def _process_queue(self):
        while self.running:
            try:
                event: OutputEvent = self.output_queue.get(timeout=1)
                logger.info(f"Event received: {event.content}")
                self.output_queue.task_done()
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing event in {self.name}: {e}")

    @classmethod
    def handled_events(cls) -> List[OutputEventType]:
        """Eventi gestiti da questa Port (tutti gli OutputEvent)"""
        return list(OutputEventType)

