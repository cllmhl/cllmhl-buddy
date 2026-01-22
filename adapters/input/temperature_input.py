"""
Temperature/Humidity Input Adapter - DHT11 sensor
"""

import os
import logging
import threading
import time
from queue import PriorityQueue, Queue
from typing import Optional

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

from adapters.ports import InputPort
from core.events import create_input_event, InputEventType, EventPriority

logger = logging.getLogger(__name__)


class TemperatureInput(InputPort):
    """
    DHT11 Temperature/Humidity Input Adapter.
    Rileva temperatura e umidità tramite sensore GPIO.
    """
    
    def __init__(self, name: str, config: dict, input_queue: PriorityQueue, interrupt_queue: Queue):
        super().__init__(name, config, input_queue, interrupt_queue)
        
        # Configurazione DHT11
        self.pin = config['pin']
        self.interval = config['interval']
        
        # Hardware
        self.dht11 = None
        self.worker_thread = None
        
        # Cache per DHT11 (richiede min 2s tra letture)
        self.last_read_time = 0
        self.min_read_interval = 2.0
        self.last_temperature = None
        self.last_humidity = None
        
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
            # Ottieni dinamicamente il pin corretto da board
            board_pin = getattr(board, f'D{self.pin}')
            self.dht11 = adafruit_dht.DHT11(board_pin)
            logger.info(f"✅ DHT11 initialized on GPIO {self.pin}")
        except AttributeError:
            logger.error(f"⚠️ Pin GPIO {self.pin} non valido. Controlla la documentazione di 'board'.")
            self.dht11 = None
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
        logger.info(f"⏸️  Stopping {self.name}...")
        self.running = False
        
        # Aspetta thread con timeout
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=3.0)
            if self.worker_thread.is_alive():
                logger.warning(f"⚠️  {self.name} thread did not terminate")
        
        # Cleanup hardware
        if self.dht11:
            try:
                self.dht11.exit()
                logger.debug("DHT11 cleanup done")
            except (AttributeError, RuntimeError) as e:
                # DHT11 già chiuso o non inizializzato
                logger.debug(f"DHT11 exit: {e}")
        
        logger.info(f"⏹️  {self.name} stopped")
    
    def _worker_loop(self) -> None:
        """Worker per DHT11 (polling periodico)"""
        logger.info("🌡️  DHT11 worker loop started")

        while self.running:
            temperature = None
            humidity = None
            try:
                # Tenta di leggere i dati dal sensore
                current_time = time.time()
                if current_time - self.last_read_time >= self.min_read_interval:
                    if self.dht11:
                        temperature = self.dht11.temperature
                        humidity = self.dht11.humidity
                        self.last_read_time = current_time
                        # Aggiorna cache solo con letture valide
                        if temperature is not None and humidity is not None:
                            self.last_temperature = temperature
                            self.last_humidity = humidity
                else:
                    # Usa valori in cache se l'intervallo minimo non è passato
                    temperature = self.last_temperature
                    humidity = self.last_humidity

                if temperature is not None and humidity is not None:
                    logger.debug(f"🌡️  Lettura DHT11: T={temperature:.1f}°C, H={humidity:.1f}%")
                    
                    # Invia evento a ogni intervallo
                    climate_event = create_input_event(
                        InputEventType.SENSOR_TEMPERATURE,
                        temperature,
                        source=self.name,
                        priority=EventPriority.LOW,
                        metadata={
                            'temperature': temperature,
                            'humidity': humidity,
                            'unit': 'celsius',
                            'sensor': 'DHT11'
                        }
                    )
                    self.input_queue.put(climate_event)
                    logger.info(f"🌡️  Evento DHT11 inviato: T={temperature:.1f}°C, H={humidity:.1f}%")

            except RuntimeError as e:
                # Errore comune con DHT11, non critico
                logger.debug(f"Errore lettura DHT11 (normale): {e}")
            except Exception as e:
                logger.error(f"Errore inatteso nel worker DHT11: {e}", exc_info=True)
            
            # Attendi l'intervallo configurato prima della prossima lettura
            time.sleep(self.interval)
