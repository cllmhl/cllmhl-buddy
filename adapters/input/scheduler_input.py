import logging
import threading
import time
from queue import PriorityQueue

from adapters.ports import InputPort
from core.events import create_input_event, InputEventType, EventPriority
from core.state import global_state

logger = logging.getLogger(__name__)

class SchedulerInput(InputPort):
    """
    Scheduler Input Adapter.
    Genera eventi a intervalli predefiniti (e.g., trigger archivista).
    """

    def __init__(self, name: str, config: dict, input_queue: PriorityQueue):
        super().__init__(name, config, input_queue)
        self.light_off_timeout = int(config["light_off_timeout"])
        self.conversation_chat_timeout = int(config["conversation_chat_timeout"])
        self.light_control_enabled = config["light_control_enabled"]
        self.light_control_start_hour = int(config["light_control_start_hour"])
        self.light_control_end_hour = int(config["light_control_end_hour"])

        self.last_processed_conversation_end = 0.0
        self.worker_thread = None
        logger.info(f"⏰ SchedulerInput initialized (light_off_timeout: {self.light_off_timeout}s, chat_timeout: {self.conversation_chat_timeout}s, light_control: {self.light_control_enabled}, {self.light_control_start_hour}-{self.light_control_end_hour})")

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
            current_hour = time.localtime().tm_hour
            time.sleep(1)  # Controlla ogni secondo
            if not self.running:
                break

            self._check_chat_timeout()

            # Controlla luci in base alla configurazione
            if self.light_control_enabled:
                if self.light_control_start_hour > self.light_control_end_hour:
                    # Caso in cui scavalca la mezzanotte (es. 17 - 9)
                    if current_hour >= self.light_control_start_hour or current_hour < self.light_control_end_hour:
                        self._check_lights()
                else:
                    # Caso nello stesso giorno (es. 8 - 20)
                    if self.light_control_start_hour <= current_hour < self.light_control_end_hour:
                        self._check_lights()

    def _check_chat_timeout(self) -> None:
        """Controlla se è necessario resettare la sessione chat per inattività"""
        if global_state.last_conversation_start is None or global_state.last_conversation_end is None:
            return
            
        # Se siamo in conversazione, ignoriamo
        if global_state.last_conversation_start > global_state.last_conversation_end:
            return
            
        # Se abbiamo già processato questo evento di fine conversazione, ignoriamo
        if global_state.last_conversation_end == self.last_processed_conversation_end:
            return
            
        # Se è passato il tempo di timeout
        if time.time() - global_state.last_conversation_end >= self.conversation_chat_timeout:
            reset_event = create_input_event(
                InputEventType.CHAT_SESSION_RESET,
                None,
                source=self.name,
                priority=EventPriority.LOW,
                metadata={"reason": "timeout", "timeout_seconds": self.conversation_chat_timeout}
            )
            self.input_queue.put(reset_event)
            logger.info(f"⏳ Chat session reset triggered (timeout: {self.conversation_chat_timeout}s)")
            
            # Segniamo come processato per non inviarlo di nuovo per la stessa sessione
            self.last_processed_conversation_end = global_state.last_conversation_end

            # Facciamo partire anche un nuovo trigger archivista
            archivist_event = create_input_event(
                InputEventType.TRIGGER_ARCHIVIST,
                None,
                source=self.name,
                priority=EventPriority.LOW
            )
            self.input_queue.put(archivist_event)
            logger.info("⏰ Archivist trigger event sent)")

    def _check_lights(self) -> None:
        # senza stato non faccio nulla
        if not global_state.last_presence or not global_state.last_absence:
            return
        
        # presenza e luse accesa: ignoro
        if (global_state.last_presence > global_state.last_absence) and global_state.is_light_on:
            return
        
        # assenza e luce spenta: ignoro
        if (global_state.last_absence > global_state.last_presence) and not global_state.is_light_on:
            return
        
        # presenza e luce spenta: accendo
        if (global_state.last_presence > global_state.last_absence):
            light_on_event = create_input_event(
                InputEventType.LIGHT_ON,
                None,
                source=self.name,
                priority=EventPriority.LOW,
                metadata={}
            )
            self.input_queue.put(light_on_event)
            logger.info("💡 Light on event sent")
            global_state.is_light_on = True
            return
        
        # assenza e luce accesa se arrivo qui! spengo dopo timeout
        if (time.time() - global_state.last_absence) >= self.light_off_timeout:
            light_off_event = create_input_event(
                InputEventType.LIGHT_OFF,
                None,
                source=self.name,
                priority=EventPriority.LOW,
                metadata={"timeout_seconds": self.light_off_timeout}
            )
            self.input_queue.put(light_off_event)
            logger.info(f"💡 Light off event sent (timeout: {self.light_off_timeout}s)")
            global_state.is_light_on = False
