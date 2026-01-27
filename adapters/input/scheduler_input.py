import logging
import threading
import time
from queue import PriorityQueue

from adapters.ports import InputPort
from core.events import create_input_event, InputEventType, EventPriority

logger = logging.getLogger(__name__)

class SchedulerInput(InputPort):
    """
    Scheduler Input Adapter.
    Genera eventi a intervalli predefiniti (e.g., trigger archivista).
    """

    def __init__(self, name: str, config: dict, input_queue: PriorityQueue):
        super().__init__(name, config, input_queue)
        self.archivist_interval = config["archivist_interval"]
        self.worker_thread = None
        logger.info(f"⏰ SchedulerInput initialized (archivist_interval: {self.archivist_interval}s)")

    def start(self) -> None:
        self.running = True
        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name=f"{self.name}_scheduler"
        )
        self.worker_thread.start()
        logger.info("▶️  SchedulerInput worker started")

    def stop(self) -> None:
        logger.info(f"⏸️  Stopping {self.name}...")
        self.running = False
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=3.0)
            if self.worker_thread.is_alive():
                logger.warning(f"⚠️  {self.name} thread did not terminate")
        logger.info(f"⏹️  {self.name} stopped")

    def _worker_loop(self) -> None:
        logger.info("⏰ SchedulerInput worker loop started")
        while self.running:
            time.sleep(self.archivist_interval)
            if not self.running:
                break

            # Trigger archivista
            archivist_event = create_input_event(
                InputEventType.TRIGGER_ARCHIVIST,
                None,
                source=self.name,
                priority=EventPriority.LOW,
                metadata={"interval_seconds": self.archivist_interval}
            )
            self.input_queue.put(archivist_event)
            logger.debug(f"⏰ Archivist trigger event sent (interval: {self.archivist_interval}s)")
