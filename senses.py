"""
Buddy Senses Module - INPUT
Modulo isolato per la lettura dei sensori fisici.
Scrive eventi nella event_queue condivisa.
"""

import os
import time
import logging
import threading
import queue
import serial
from dataclasses import dataclass
from typing import Optional, Any

# Mock GPIO per testing
if not os.path.exists('/proc/device-tree/model'):
    os.environ['GPIOZERO_PIN_FACTORY'] = 'mock'

try:
    import adafruit_dht
    import board
    DHT_AVAILABLE = True
except ImportError:
    DHT_AVAILABLE = False
    logging.warning("⚠️ adafruit_dht/board non disponibile. DHT11 disabilitato.")

logger = logging.getLogger()

@dataclass
class SensorEvent:
    """Evento generato da un sensore."""
    sensor_type: str    # "radar", "temperature", "humidity", "light"
    value: Any          # Il valore del sensore
    timestamp: float
    metadata: Optional[dict] = None  # Info aggiuntive

# =============================================================================
# RADAR mmWave LD2410C (UART/Serial)
# =============================================================================
class RadarLD2410C:
    """
    Gestisce il radar mmWave LD2410C per rilevamento presenza e movimento.
    
    Protocollo:
    - Il sensore comunica via UART (Serial)
    - Formato frame: Header(4) + Command(2) + Length(2) + Data(N) + Tail(4)
    - Header: FD FC FB FA
    - Tail: 04 03 02 01
    """
    
    def __init__(self, port='/dev/ttyAMA0', baudrate=256000, enabled=True):
        self.port = port
        self.baudrate = baudrate
        self.enabled = enabled
        self.serial_conn = None
        self.running = False
        
        # Stati
        self.presence_detected = False
        self.movement_detected = False
        self.static_detected = False
        self.distance = 0  # cm
        
        if not self.enabled:
            logger.info("📡 RadarLD2410C disabilitato (configurazione)")
            return
            
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1.0
            )
            logger.info(f"📡 RadarLD2410C connesso su {self.port} @ {self.baudrate}")
        except Exception as e:
            logger.warning(f"⚠️ Errore connessione RadarLD2410C: {e}. Sensore disabilitato.")
            self.enabled = False
    
    def read_data(self) -> Optional[dict]:
        """
        Legge e decodifica i dati dal radar.
        Ritorna dizionario con: presence, movement, static, distance
        """
        if not self.enabled or not self.serial_conn:
            return None
            
        try:
            # Cerca header frame: FD FC FB FA
            if self.serial_conn.in_waiting > 0:
                data = self.serial_conn.read(self.serial_conn.in_waiting)
                
                # Cerca il pattern header nel buffer
                header = b'\xFD\xFC\xFB\xFA'
                idx = data.find(header)
                
                if idx != -1:
                    # Frame trovato, parsing base
                    # Struttura tipica per report target engineering mode:
                    # Bytes 5-6: Target state (00=no target, 01=moving, 02=static, 03=both)
                    # Bytes 7-8: Movement distance (cm)
                    # Bytes 9: Movement energy
                    # Bytes 10-11: Static distance (cm)
                    # Bytes 12: Static energy
                    
                    if len(data) >= idx + 23:  # Frame completo minimo
                        target_state = data[idx + 5] if len(data) > idx + 5 else 0
                        
                        presence = target_state > 0
                        movement = target_state in [1, 3]
                        static = target_state in [2, 3]
                        
                        # Distanza dal target in movimento (se presente)
                        if len(data) >= idx + 8:
                            distance = data[idx + 7] + (data[idx + 8] << 8) if movement else 0
                        else:
                            distance = 0
                        
                        # Aggiorna stato interno
                        self.presence_detected = presence
                        self.movement_detected = movement
                        self.static_detected = static
                        self.distance = distance
                        
                        return {
                            'presence': presence,
                            'movement': movement,
                            'static': static,
                            'distance': distance
                        }
                        
        except Exception as e:
            logger.error(f"Errore lettura RadarLD2410C: {e}")
            
        return None
    
    def close(self):
        """Chiude la connessione seriale."""
        if self.serial_conn:
            try:
                self.serial_conn.close()
                logger.info("📡 RadarLD2410C disconnesso")
            except:
                pass

# =============================================================================
# DHT11 - Sensore Temperatura e Umidità
# =============================================================================
class DHT11Sensor:
    """
    Gestisce il sensore DHT11 per temperatura e umidità.
    Richiede libreria adafruit-circuitpython-dht
    """
    
    def __init__(self, pin=4, enabled=True):
        """
        Args:
            pin: GPIO pin number (BCM numbering)
            enabled: Se False, il sensore non viene inizializzato
        """
        self.pin = pin
        self.enabled = enabled and DHT_AVAILABLE
        self.sensor = None
        
        # Cache per evitare letture troppo frequenti (DHT11 richiede 2s tra letture)
        self.last_read_time = 0
        self.min_read_interval = 2.0  # secondi
        self.last_temperature = None
        self.last_humidity = None
        
        if not DHT_AVAILABLE:
            logger.warning("⚠️ DHT11 disabilitato: libreria adafruit-dht non disponibile")
            self.enabled = False
            return
            
        if not self.enabled:
            logger.info("🌡️  DHT11 disabilitato (configurazione)")
            return
            
        try:
            # Mappa GPIO pin a board pin
            pin_map = {
                4: board.D4,
                17: board.D17,
                27: board.D27,
                22: board.D22,
                23: board.D23,
                24: board.D24,
            }
            
            if self.pin not in pin_map:
                logger.warning(f"⚠️ GPIO{self.pin} non mappato. DHT11 disabilitato.")
                self.enabled = False
                return
                
            board_pin = pin_map[self.pin]
            self.sensor = adafruit_dht.DHT11(board_pin)
            logger.info(f"🌡️  DHT11 inizializzato su GPIO{self.pin}")
            
        except Exception as e:
            logger.warning(f"⚠️ Errore init DHT11: {e}. Sensore disabilitato.")
            self.enabled = False
    
    def read_temperature(self) -> Optional[float]:
        """Legge la temperatura in gradi Celsius."""
        if not self.enabled or not self.sensor:
            return None
            
        current_time = time.time()
        if current_time - self.last_read_time < self.min_read_interval:
            return self.last_temperature
            
        try:
            temp = self.sensor.temperature
            self.last_temperature = temp
            self.last_read_time = current_time
            return temp
        except RuntimeError as e:
            # DHT11 genera spesso errori di lettura, è normale
            logger.debug(f"DHT11 read error (normale): {e}")
            return self.last_temperature
        except Exception as e:
            logger.error(f"Errore lettura temperatura DHT11: {e}")
            return None
    
    def read_humidity(self) -> Optional[float]:
        """Legge l'umidità in percentuale."""
        if not self.enabled or not self.sensor:
            return None
            
        current_time = time.time()
        if current_time - self.last_read_time < self.min_read_interval:
            return self.last_humidity
            
        try:
            humidity = self.sensor.humidity
            self.last_humidity = humidity
            self.last_read_time = current_time
            return humidity
        except RuntimeError as e:
            logger.debug(f"DHT11 read error (normale): {e}")
            return self.last_humidity
        except Exception as e:
            logger.error(f"Errore lettura umidità DHT11: {e}")
            return None
    
    def read_both(self) -> tuple[Optional[float], Optional[float]]:
        """Legge sia temperatura che umidità in una sola chiamata."""
        if not self.enabled or not self.sensor:
            return None, None
            
        current_time = time.time()
        if current_time - self.last_read_time < self.min_read_interval:
            return self.last_temperature, self.last_humidity
            
        try:
            temp = self.sensor.temperature
            humidity = self.sensor.humidity
            self.last_temperature = temp
            self.last_humidity = humidity
            self.last_read_time = current_time
            return temp, humidity
        except RuntimeError as e:
            logger.debug(f"DHT11 read error (normale): {e}")
            return self.last_temperature, self.last_humidity
        except Exception as e:
            logger.error(f"Errore lettura DHT11: {e}")
            return None, None
    
    def close(self):
        """Cleanup del sensore."""
        if self.sensor:
            try:
                self.sensor.exit()
            except:
                pass

# =============================================================================
# SENSOR MANAGER - Orchestratore di tutti i sensori
# =============================================================================
class BuddySenses:
    """
    Manager centrale per tutti i sensori fisici.
    Legge i sensori e invia eventi nella event_queue.
    """
    
    def __init__(self, event_queue: queue.Queue, config: Optional[dict] = None):
        """
        Args:
            event_queue: Coda condivisa per inviare eventi al main loop
            config: Dizionario di configurazione per i sensori
        """
        self.event_queue = event_queue
        self.running = False
        
        # Configurazione default
        if config is None:
            config = {}
        
        # Inizializza sensori
        self.radar = RadarLD2410C(
            port=config.get('radar_port', '/dev/ttyAMA0'),
            baudrate=config.get('radar_baudrate', 256000),
            enabled=config.get('radar_enabled', True)
        )
        
        self.dht11 = DHT11Sensor(
            pin=config.get('dht11_pin', 4),
            enabled=config.get('dht11_enabled', True)
        )
        
        # Intervalli di lettura (secondi)
        self.radar_interval = config.get('radar_interval', 0.5)
        self.dht11_interval = config.get('dht11_interval', 30.0)
        
        # Timestamp ultime letture
        self.last_radar_read = 0
        self.last_dht11_read = 0
        
        # Stati precedenti per rilevare cambiamenti
        self.prev_presence = False
        self.prev_temperature = None
        self.prev_humidity = None
        
        logger.info("👁️  BuddySenses inizializzato")
    
    def _check_radar(self):
        """Legge il radar e invia eventi se ci sono cambiamenti."""
        current_time = time.time()
        
        if current_time - self.last_radar_read < self.radar_interval:
            return
            
        self.last_radar_read = current_time
        
        data = self.radar.read_data()
        if data is None:
            return
        
        # Evento per cambio presenza
        if data['presence'] != self.prev_presence:
            self.prev_presence = data['presence']
            
            event = SensorEvent(
                sensor_type="radar_presence",
                value=data['presence'],
                timestamp=current_time,
                metadata={
                    'movement': data['movement'],
                    'static': data['static'],
                    'distance': data['distance']
                }
            )
            
            try:
                self.event_queue.put(event, block=False)
                logger.info(f"📡 Presenza: {data['presence']} | Movimento: {data['movement']} | Distanza: {data['distance']}cm")
            except queue.Full:
                logger.warning("Event queue piena, evento radar scartato")
    
    def _check_dht11(self):
        """Legge temperatura e umidità e invia eventi se cambiano significativamente."""
        current_time = time.time()
        
        if current_time - self.last_dht11_read < self.dht11_interval:
            return
            
        self.last_dht11_read = current_time
        
        temp, humidity = self.dht11.read_both()
        
        # Invia evento se temperatura cambia di almeno 0.5°C
        if temp is not None:
            if self.prev_temperature is None or abs(temp - self.prev_temperature) >= 0.5:
                self.prev_temperature = temp
                
                event = SensorEvent(
                    sensor_type="temperature",
                    value=temp,
                    timestamp=current_time,
                    metadata={'unit': 'celsius'}
                )
                
                try:
                    self.event_queue.put(event, block=False)
                    logger.info(f"🌡️  Temperatura: {temp:.1f}°C")
                except queue.Full:
                    logger.warning("Event queue piena, evento temperatura scartato")
        
        # Invia evento se umidità cambia di almeno 2%
        if humidity is not None:
            if self.prev_humidity is None or abs(humidity - self.prev_humidity) >= 2.0:
                self.prev_humidity = humidity
                
                event = SensorEvent(
                    sensor_type="humidity",
                    value=humidity,
                    timestamp=current_time,
                    metadata={'unit': 'percent'}
                )
                
                try:
                    self.event_queue.put(event, block=False)
                    logger.info(f"💧 Umidità: {humidity:.1f}%")
                except queue.Full:
                    logger.warning("Event queue piena, evento umidità scartato")
    
    def sensor_loop(self):
        """Loop principale di lettura sensori."""
        logger.info("👁️  BuddySenses loop avviato")
        
        while self.running:
            try:
                # Polling sensori
                self._check_radar()
                self._check_dht11()
                
                # Piccolo sleep per non sovraccaricare la CPU
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Errore in sensor loop: {e}")
                time.sleep(1)  # Pausa più lunga in caso di errore
        
        logger.info("👁️  BuddySenses loop terminato")
    
    def start(self):
        """Avvia il thread di lettura sensori."""
        self.running = True
        thread = threading.Thread(
            target=self.sensor_loop,
            daemon=True,
            name="SensesThread"
        )
        thread.start()
        logger.info("👁️  BuddySenses thread avviato")
    
    def stop(self):
        """Ferma il thread di lettura sensori."""
        self.running = False
        self.radar.close()
        self.dht11.close()
        logger.info("👁️  BuddySenses arrestato")

# =============================================================================
# TEST / ESEMPIO D'USO
# =============================================================================
if __name__ == "__main__":
    # Setup logging per test
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Crea una coda di test
    test_queue = queue.Queue()
    
    # Configurazione sensori da variabili d'ambiente
    config = {
        'radar_enabled': os.getenv('RADAR_ENABLED', 'true').lower() == 'true',
        'radar_port': os.getenv('RADAR_PORT', '/dev/ttyAMA10'),
        'radar_baudrate': int(os.getenv('RADAR_BAUDRATE', '256000')),
        'radar_interval': float(os.getenv('RADAR_INTERVAL', '0.5')),
        'dht11_enabled': os.getenv('DHT11_ENABLED', 'true').lower() == 'true',
        'dht11_pin': int(os.getenv('DHT11_PIN', '4')),
        'dht11_interval': float(os.getenv('DHT11_INTERVAL', '5.0'))  # Più frequente per testing
    }
    
    # Inizializza e avvia
    senses = BuddySenses(test_queue, config)
    senses.start()
    
    print("\n🧪 Test BuddySenses - Premi Ctrl+C per terminare\n")
    
    try:
        while True:
            # Leggi eventi dalla coda
            if not test_queue.empty():
                event = test_queue.get()
                print(f"📨 Evento: {event.sensor_type} = {event.value} | {event.metadata}")
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Arresto test...")
        senses.stop()
        print("✅ Test completato")
