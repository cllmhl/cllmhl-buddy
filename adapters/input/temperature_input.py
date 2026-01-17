"""
Temperature/Humidity Input Adapter - DHT11 sensor
"""

import os
import logging
import threading
import time
from queue import PriorityQueue

# Mock GPIO per testing
if not os.path.exists('/proc/device-tree/model'):
    os.environ['GPIOZERO_PIN_FACTORY'] = 'mock'

# DHT11 imports (opzionali)
try:
    import adafruit_dht
    import board
    DHT_AVAILABLE = True
except ImportError:
    DHT_AVAILABLE = False
    logging.warning("⚠️ adafruit_dht not available. DHT11 disabled.")

from adapters.ports import TemperatureInputPort
from core.events import create_input_event, EventType, EventPriority

logger = logging.getLogger(__name__)


class TemperatureInput(TemperatureInputPort):
    """
    DHT11 Temperature/Humidity Input Adapter.
    Rileva temperatura e umidità tramite sensore GPIO.
    """
    
    def __init__(self, name: str, config: dict, input_queue: PriorityQueue):
        super().__init__(name, config, input_queue)
        
        # Configurazione DHT11
        self.pin = config.get('pin', 4)
        self.interval = config.get('interval', 30.0)
        
        # Hardware
        self.dht11 = None
        self.worker_thread = None
        
        # Setup DHT11
        self._setup_dht11()
        
        logger.info(
            f"🌡️  TemperatureInput initialized "
            f"(pin: {self.pin}, interval: {self.interval}s)"
        )
    
    def _setup_dht11(self) -> None:
        """Setup DHT11 sensor"""
        if not DHT_AVAILABLE:
            logger.warning("⚠️ DHT11 library not available")
            return
        
        try:
            # Map pin number to board pin
            pin_map = {
                4: board.D4,
                17: board.D17,
                18: board.D18,
                27: board.D27,
                22: board.D22,
                23: board.D23,
                24: board.D24
            }
            
            board_pin = pin_map.get(self.pin, board.D4)
            self.dht11 = adafruit_dht.DHT11(board_pin)
            logger.info(f"✅ DHT11 initialized on GPIO {self.pin}")
        except Exception as e:
            logger.warning(f"⚠️ DHT11 initialization failed: {e}")
            self.dht11 = None
    
    def start(self) -> None:
        """Avvia worker thread"""
        self.running = True
        
        if self.dht11:
            self.worker_thread = threading.Thread(
                target=self._worker_loop,
                daemon=True,
                name=f"{self.name}_dht11"
            )
            self.worker_thread.start()
            logger.info("▶️  DHT11 worker started")
        else:
            logger.warning("⚠️ DHT11 not available, worker not started")
        
        logger.info(f"▶️  {self.name} started")
    
    def stop(self) -> None:
        """Ferma worker thread"""
        self.running = False
        
        if self.worker_thread:
            self.worker_thread.join(timeout=2.0)
        
        # Cleanup hardware
        if self.dht11:
            try:
                self.dht11.exit()
            except (AttributeError, RuntimeError) as e:
                # DHT11 già chiuso o non inizializzato
                logger.debug(f"DHT11 exit: {e}")
        
        logger.info(f"⏹️  {self.name} stopped")
    
    def _worker_loop(self) -> None:
        """Worker per DHT11 (polling periodico)"""
        logger.info("🌡️  DHT11 worker loop started")
        
        # Stati precedenti per rilevare cambiamenti significativi
        prev_temperature = None
        prev_humidity = None
        
        while self.running:
            try:
                # Leggi temperatura e umidità
                temperature = self.dht11.temperature
                humidity = self.dht11.humidity
                
                if temperature is not None and humidity is not None:
                    logger.debug(f"🌡️  T={temperature:.1f}°C, H={humidity:.1f}%")
                    
                    # Invia evento temperatura solo se cambia di almeno 0.5°C
                    if prev_temperature is None or abs(temperature - prev_temperature) >= 0.5:
                        prev_temperature = temperature
                        
                        temp_event = create_input_event(
                            EventType.SENSOR_TEMPERATURE,
                            temperature,
                            source="dht11",
                            priority=EventPriority.LOW,
                            metadata={'unit': 'celsius'}
                        )
                        self.input_queue.put(temp_event)
                        logger.info(f"🌡️  Temperatura: {temperature:.1f}°C")
                    
                    # Invia evento umidità solo se cambia di almeno 5%
                    if prev_humidity is None or abs(humidity - prev_humidity) >= 5.0:
                        prev_humidity = humidity
                        
                        humidity_event = create_input_event(
                            EventType.SENSOR_HUMIDITY,
                            humidity,
                            source="dht11",
                            priority=EventPriority.LOW,
                            metadata={'unit': 'percent'}
                        )
                        self.input_queue.put(humidity_event)
                        logger.info(f"💧 Umidità: {humidity:.1f}%")
            
            except RuntimeError as e:
                # DHT11 spesso fallisce letture singole - è normale
                logger.debug(f"DHT11 read error (expected): {e}")
            except KeyboardInterrupt:
                logger.info("Temperature worker interrupted by user")
                break
            except Exception as e:
                logger.error(f"DHT11 worker error: {e}", exc_info=True)
            
            # Attendi intervallo
            time.sleep(self.interval)


class MockTemperatureInput(TemperatureInputPort):
    """
    Mock Temperature Input per testing.
    Genera dati fake per simulare sensore temperatura/umidità.
    """
    
    def __init__(self, name: str, config: dict, input_queue: PriorityQueue):
        super().__init__(name, config, input_queue)
        
        self.interval = config.get('interval', 10.0)
        self.worker_thread = None
        
        logger.info(f"🌡️  MockTemperatureInput initialized")
    
    def start(self) -> None:
        """Avvia worker"""
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
        """Loop che genera dati fake"""
        import random
        
        while self.running:
            try:
                # Temperatura random 18-28°C
                temp = random.uniform(18.0, 28.0)
                humidity = random.uniform(40.0, 70.0)
                
                logger.info(f"🌡️  [MOCK] T={temp:.1f}°C, H={humidity:.1f}%")
                
                temp_event = create_input_event(
                    EventType.SENSOR_TEMPERATURE,
                    temp,
                    source="mock_dht11",
                    priority=EventPriority.LOW
                )
                self.input_queue.put(temp_event)
                
                humidity_event = create_input_event(
                    EventType.SENSOR_HUMIDITY,
                    humidity,
                    source="mock_dht11",
                    priority=EventPriority.LOW
                )
                self.input_queue.put(humidity_event)
            
            except Exception as e:
                logger.error(f"Mock temperature error: {e}")
            
            time.sleep(self.interval)
