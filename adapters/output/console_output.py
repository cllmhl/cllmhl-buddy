"""
Console Output Adapter - Output debug in console
Utile per test hardware e development
"""

import logging
import threading
from queue import PriorityQueue, Empty

from adapters.ports import OutputPort
from core.events import Event, InputEventType, OutputEventType

logger = logging.getLogger(__name__)


class ConsoleOutputPort(OutputPort):
    """Port per output console"""
    

    @classmethod
    def handled_events(cls):
        return [
            InputEventType.SENSOR_PRESENCE,
            InputEventType.SENSOR_MOVEMENT, 
            InputEventType.SENSOR_TEMPERATURE,
            InputEventType.SENSOR_HUMIDITY,
            InputEventType.USER_SPEECH,
            OutputEventType.SPEAK
        ]


class ConsoleOutput(ConsoleOutputPort):
    """Stampa eventi in console con formattazione"""
    
    def __init__(self, name: str, config: dict):
        queue_maxsize = config.get('queue_maxsize', 100)
        super().__init__(name, config, queue_maxsize)
        self.verbose = config.get('verbose', False)
        self.worker_thread = None
    
    def start(self):
        self.running = True
        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name=f"{self.name}_worker"
        )
        self.worker_thread.start()
        logger.info(f"▶️  {self.name} started")
    
    def stop(self):
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=1.0)
        logger.info(f"⏹️  {self.name} stopped")
    
    def _worker_loop(self):
        while self.running:
            try:
                event = self.output_queue.get(timeout=0.5)
                self._print_event(event)
                self.output_queue.task_done()
            except Empty:
                continue
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Console output error: {e}")
    
    def _print_event(self, event: Event):
        """Formatta e stampa evento"""
        icons = {
            InputEventType.SENSOR_PRESENCE: "👤",
            InputEventType.SENSOR_MOVEMENT: "🏃",
            InputEventType.SENSOR_TEMPERATURE: "🌡️",
            InputEventType.SENSOR_HUMIDITY: "💧",
            InputEventType.USER_SPEECH: "🎤",
            OutputEventType.SPEAK: "🔊"
        }
        
        icon = icons.get(event.type, "📊")
        
        if event.type == InputEventType.SENSOR_PRESENCE:
            status = "PRESENTE" if event.content else "ASSENTE"
            msg = f"{icon} Presenza: {status}"
            if self.verbose and event.metadata:
                msg += f" | Dist: {event.metadata.get('distance', 0)}cm"
                msg += f" | Mov: {event.metadata.get('mov_energy', 0)}"
        
        elif event.type == InputEventType.SENSOR_TEMPERATURE:
            temp = event.content
            msg = f"{icon} Temperatura: {temp}°C"
            if self.verbose and event.metadata:
                hum = event.metadata.get('humidity')
                if hum:
                    msg += f" | 💧 {hum}%"
        
        elif event.type == InputEventType.SENSOR_HUMIDITY:
            hum = event.content
            msg = f"{icon} Umidità: {hum}%"
        
        elif event.type == InputEventType.USER_SPEECH:
            msg = f"{icon} Utente: {event.content}"
        
        elif event.type == OutputEventType.SPEAK:
            msg = f"{icon} Buddy: {event.content}"
        
        else:
            msg = f"{icon} {event.type.name}: {event.content}"
        
        print(f"\r{msg}                    ", flush=True)


class MockConsoleOutput(ConsoleOutputPort):
    """Mock console output per test"""
    
    def __init__(self, name: str, config: dict):
        queue_maxsize = config.get('queue_maxsize', 100)
        super().__init__(name, config, queue_maxsize)
        self.worker_thread = None
    
    def start(self):
        self.running = True
        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name=f"{self.name}_worker"
        )
        self.worker_thread.start()
        logger.info(f"▶️  {self.name} started (MOCK)")
    
    def stop(self):
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=1.0)
    
    def _worker_loop(self):
        while self.running:
            try:
                event = self.output_queue.get(timeout=0.5)
                logger.debug(f"MOCK Console: {event.type.name}")
                self.output_queue.task_done()
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Mock console error: {e}")
