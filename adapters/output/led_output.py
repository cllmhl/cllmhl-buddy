"""
LED Output Adapters - Controllo LED
"""

import os
import logging
import threading
import time
from queue import PriorityQueue, Empty
from typing import Optional

# Mock GPIO per testing
if not os.path.exists('/proc/device-tree/model'):
    os.environ['GPIOZERO_PIN_FACTORY'] = 'mock'

from gpiozero import LED

from adapters.ports import OutputPort
from core.events import Event, OutputEventType

logger = logging.getLogger(__name__)


class GPIOLEDOutput(OutputPort):
    """
    LED Output con GPIO reale (Raspberry Pi).
    """
    
    def __init__(self, name: str, config: dict):
        queue_maxsize = config['queue_maxsize']
        super().__init__(name, config, queue_maxsize)
        # Pin configuration
        self.led_ascolto_pin = config['led_ascolto_pin']  # Blu
        self.led_parlo_pin = config['led_parlo_pin']      # Verde (rinominato)
        # Blink timing configuration
        self.blink_on_time = config['blink_on_time']
        self.blink_off_time = config['blink_off_time']
        
        # Initialize LEDs
        # LED sono CRITICI per questo adapter - fail se non disponibili
        try:
            self.led_ascolto = LED(self.led_ascolto_pin)
            self.led_parlo = LED(self.led_parlo_pin)
            logger.info(f"✅ LEDs initialized: Ascolto(GPIO{self.led_ascolto_pin}), Parlo(GPIO{self.led_parlo_pin})")
        except Exception as e:
            logger.error(f"❌ LED initialization failed: {e}")
            logger.error("LEDOutputPort requires working LEDs - cannot continue")
            raise RuntimeError(f"LED initialization failed: {e}") from e
        
        self.worker_thread: Optional[threading.Thread] = None
    
    @classmethod
    def handled_events(cls):
        """Eventi gestiti da questo adapter"""
        return [OutputEventType.LED_CONTROL]
    
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
        """Ferma worker e spegne LED"""
        logger.info(f"⏸️  Stopping {self.name}...")
        self.running = False
        
        # Aspetta thread con timeout
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=3.0)
            if self.worker_thread.is_alive():
                logger.warning(f"⚠️  {self.name} thread did not terminate")
        
        # Spegni tutti i LED
        if self.led_ascolto:
            try:
                self.led_ascolto.off()
            except Exception as e:
                logger.debug(f"LED ascolto cleanup error: {e}")
        if self.led_parlo:
            try:
                self.led_parlo.off()
            except Exception as e:
                logger.debug(f"LED parlo cleanup error: {e}")
        
        logger.info(f"⏹️  {self.name} stopped")
    
    def _worker_loop(self) -> None:
        """Loop principale"""
        while self.running:
            try:
                event = self.output_queue.get(timeout=0.5)
                
                if event.type == OutputEventType.LED_CONTROL:
                    self._handle_led_control(event)
                else:
                    logger.warning(f"Unknown LED event type: {event.type}")
                
                self.output_queue.task_done()
                
            except Empty:
                continue
            except KeyboardInterrupt:
                logger.info("LED worker interrupted")
                break
            except Exception as e:
                logger.error(
                    f"Error in LED worker: {e}",
                    exc_info=True  # Full stack trace per debugging
                )
                # Continue loop - un errore non deve fermare il worker
    
    def _get_led(self, led_name: str):
        """Helper per ottenere l'oggetto LED dal nome"""
        if led_name == 'ascolto':
            return self.led_ascolto
        elif led_name == 'parlo':
            return self.led_parlo
        return None
    
    def _handle_led_control(self, event: Event) -> None:
        """
        Gestisce evento LED_CONTROL unificato.
        
        Metadata attesi:
        - led: 'ascolto' | 'parlo' (required)
        - command: 'on' | 'off' | 'blink' (required)
        - continuous: True | False (per blink, default False)
        - on_time: float (per blink, default from config)
        - off_time: float (per blink, default from config)
        - times: int (per blink non continuo, default 3)
        """
        if not event.metadata:
            logger.warning("LED_CONTROL event without metadata, ignoring")
            return
        
        led_name = event.metadata.get('led')
        command = event.metadata.get('command')
        
        if not led_name or not command:
            logger.warning(f"LED_CONTROL missing led or command: {event.metadata}")
            return
        
        led = self._get_led(led_name)
        if not led:
            logger.warning(f"Unknown LED: {led_name}")
            return
        
        # Execute command
        if command == 'on':
            led.off()  # Stop any blink first
            led.on()
            logger.debug(f"💡 LED {led_name.upper()} ON")
            
        elif command == 'off':
            led.off()
            logger.debug(f"🌑 LED {led_name.upper()} OFF")
            
        elif command == 'blink':
            continuous = event.metadata.get('continuous', False)
            on_time = event.metadata.get('on_time', self.blink_on_time)
            off_time = event.metadata.get('off_time', self.blink_off_time)
            
            if continuous:
                # Continuous blink usando gpiozero native
                led.blink(on_time=on_time, off_time=off_time)
                logger.debug(f"💫 LED {led_name.upper()} BLINK CONTINUOUS ({on_time}s/{off_time}s)")
            else:
                # Blink N volte (legacy behavior)
                times = event.metadata.get('times', 3)
                led.off()  # Stop any previous blink
                for _ in range(times):
                    if not self.running:
                        break
                    led.on()
                    time.sleep(on_time)
                    led.off()
                    time.sleep(off_time)
                logger.debug(f"💫 LED {led_name.upper()} BLINK x{times}")
        
        else:
            logger.warning(f"Unknown LED command: {command}")
    
    
    # ===== LEGACY HANDLERS (backward compatibility) =====
    



class MockLEDOutput(OutputPort):
    """
    Mock LED Output per testing.
    Scrive su console invece di accendere LED.
    """
    
    def __init__(self, name: str, config: dict):
        queue_maxsize = config.get('queue_maxsize', 50)
        super().__init__(name, config, queue_maxsize)
        self.worker_thread: Optional[threading.Thread] = None
        logger.info(f"💡 MockLEDOutput initialized")
    
    @classmethod
    def handled_events(cls):
        """Eventi gestiti da questo adapter"""
        return [OutputEventType.LED_CONTROL]
    
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
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=2.0)
        
        logger.info(f"⏹️  {self.name} stopped")
    
    def _worker_loop(self) -> None:
        """Loop principale"""
        while self.running:
            try:
                event = self.output_queue.get(timeout=0.5)
                
                if event.type == OutputEventType.LED_CONTROL:
                    self._handle_mock_led_control(event)
                else:
                    logger.warning(f"Unknown LED event type: {event.type}")
                
                self.output_queue.task_done()
                
            except Empty:
                continue
            except KeyboardInterrupt:
                logger.info("Mock LED worker interrupted")
                break
            except Exception as e:
                logger.error(
                    f"Error in mock LED worker: {e}",
                    exc_info=True  # Full stack trace
                )
    
    def _handle_mock_led_control(self, event: Event) -> None:
        """Mock LED_CONTROL"""
        if not event.metadata:
            return
        
        led_name = event.metadata.get('led', 'parlo')
        command = event.metadata.get('command', 'unknown').upper()
        
        details = ""
        if command == 'BLINK':
            if event.metadata.get('continuous'):
                on_time = event.metadata.get('on_time', 1.0)
                off_time = event.metadata.get('off_time', 1.0)
                details = f" CONTINUOUS ({on_time}s/{off_time}s)"
            else:
                times = event.metadata.get('times', 3)
                details = f" x{times}"
        
        logger.info(f"💡 [MOCK LED] {led_name.upper()} -> {command}{details}")
    

