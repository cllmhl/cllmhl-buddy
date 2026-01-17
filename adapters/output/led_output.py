"""
LED Output Adapters - Controllo LED
"""

import os
import logging
import threading
import time
from queue import PriorityQueue, Empty

# Mock GPIO per testing
if not os.path.exists('/proc/device-tree/model'):
    os.environ['GPIOZERO_PIN_FACTORY'] = 'mock'

from gpiozero import LED

from adapters.ports import LEDOutputPort
from core.events import Event, EventType

logger = logging.getLogger(__name__)


class GPIOLEDOutput(LEDOutputPort):
    """
    LED Output con GPIO reale (Raspberry Pi).
    """
    
    def __init__(self, name: str, config: dict):
        queue_maxsize = config.get('queue_maxsize', 100)
        super().__init__(name, config, queue_maxsize)
        
        # Pin configuration
        self.led_ascolto_pin = config.get('led_ascolto_pin', 26)  # Blu
        self.led_stato_pin = config.get('led_stato_pin', 21)      # Verde
        
        # Initialize LEDs
        # LED sono CRITICI per questo adapter - fail se non disponibili
        try:
            self.led_ascolto = LED(self.led_ascolto_pin)
            self.led_stato = LED(self.led_stato_pin)
            logger.info(f"✅ LEDs initialized: Ascolto(GPIO{self.led_ascolto_pin}), Stato(GPIO{self.led_stato_pin})")
        except Exception as e:
            logger.error(f"❌ LED initialization failed: {e}")
            logger.error("LEDOutputPort requires working LEDs - cannot continue")
            raise RuntimeError(f"LED initialization failed: {e}") from e
        
        self.worker_thread = None
    
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
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=2.0)
        
        # Spegni tutti i LED
        if self.led_ascolto:
            self.led_ascolto.off()
        if self.led_stato:
            self.led_stato.off()
        
        logger.info(f"⏹️  {self.name} stopped")
    
    def _worker_loop(self) -> None:
        """Loop principale"""
        while self.running:
            try:
                event = self.output_queue.get(timeout=0.5)
                
                if event.type == EventType.LED_ON:
                    self._handle_led_on(event)
                elif event.type == EventType.LED_OFF:
                    self._handle_led_off(event)
                elif event.type == EventType.LED_BLINK:
                    self._handle_led_blink(event)
                
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
    
    def _handle_led_on(self, event: Event) -> None:
        """Accendi LED"""
        led_name = event.metadata.get('led', 'stato') if event.metadata else 'stato'
        
        if led_name == 'ascolto' and self.led_ascolto:
            self.led_ascolto.on()
            logger.debug("💡 LED Ascolto ON")
        elif led_name == 'stato' and self.led_stato:
            self.led_stato.on()
            logger.debug("💡 LED Stato ON")
    
    def _handle_led_off(self, event: Event) -> None:
        """Spegni LED"""
        led_name = event.metadata.get('led', 'stato') if event.metadata else 'stato'
        
        if led_name == 'ascolto' and self.led_ascolto:
            self.led_ascolto.off()
            logger.debug("🌑 LED Ascolto OFF")
        elif led_name == 'stato' and self.led_stato:
            self.led_stato.off()
            logger.debug("🌑 LED Stato OFF")
    
    def _handle_led_blink(self, event: Event) -> None:
        """Blink LED"""
        led_name = event.metadata.get('led', 'stato') if event.metadata else 'stato'
        times = event.metadata.get('times', 3) if event.metadata else 3
        
        led = None
        if led_name == 'ascolto':
            led = self.led_ascolto
        elif led_name == 'stato':
            led = self.led_stato
        
        if led:
            for _ in range(times):
                led.on()
                time.sleep(0.2)
                led.off()
                time.sleep(0.2)


class MockLEDOutput(LEDOutputPort):
    """
    Mock LED Output per testing.
    Scrive su console invece di accendere LED.
    """
    
    def __init__(self, name: str, config: dict):
        queue_maxsize = config.get('queue_maxsize', 100)
        super().__init__(name, config, queue_maxsize)
        self.worker_thread = None
        logger.info(f"💡 MockLEDOutput initialized")
    
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
                
                if event.type == EventType.LED_ON:
                    self._handle_mock_led(event, "ON")
                elif event.type == EventType.LED_OFF:
                    self._handle_mock_led(event, "OFF")
                elif event.type == EventType.LED_BLINK:
                    self._handle_mock_led(event, "BLINK")
                
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
    
    def _handle_mock_led(self, event: Event, action: str) -> None:
        """Simula LED action"""
        led_name = event.metadata.get('led', 'stato') if event.metadata else 'stato'
        logger.info(f"💡 [MOCK LED] {led_name.upper()} -> {action}")
