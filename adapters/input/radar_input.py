"""
Radar Input Adapter - Radar LD2410C presence/movement detection
"""

import logging
import threading
import time
import serial
from queue import PriorityQueue
from typing import Optional, Dict, Any

from adapters.ports import InputPort
from core.events import create_input_event, InputEventType, EventPriority

logger = logging.getLogger(__name__)


class RadarInput(InputPort):
    """
    Radar LD2410C Input Adapter.
    Rileva presenza e movimento tramite radar UART.
    """
    
    def __init__(self, name: str, config: dict, input_queue: PriorityQueue):
        super().__init__(name, config, input_queue)
        
        # Configurazione radar
        self.port = config['port']
        self.baudrate = config['baudrate']
        self.interval = config['interval']
        
        # Hardware
        self.radar = None
        self.worker_thread = None
        
        # Setup radar
        self._setup_radar()
        
        logger.info(
            f"📡 RadarInput initialized "
            f"(port: {self.port}, baudrate: {self.baudrate})"
        )
    
    def _setup_radar(self) -> None:
        """Setup Radar LD2410C"""
        try:
            self.radar = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1.0
            )
            logger.info(f"✅ Radar connected: {self.port} @ {self.baudrate}")
        except Exception as e:
            logger.warning(f"⚠️ Radar connection failed: {e}")
            self.radar = None
    
    def start(self) -> None:
        """Avvia worker thread"""
        self.running = True
        
        if self.radar:
            self.worker_thread = threading.Thread(
                target=self._worker_loop,
                daemon=True,
                name=f"{self.name}_radar"
            )
            self.worker_thread.start()
            logger.info("▶️  Radar worker started")
        else:
            logger.warning("⚠️ Radar not available, worker not started")
        
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
        if self.radar:
            try:
                self.radar.close()
                logger.debug("Radar serial closed")
            except (AttributeError, RuntimeError) as e:
                # Radar già chiuso o non inizializzato
                logger.debug(f"Radar close: {e}")
        
        logger.info(f"⏹️  {self.name} stopped")
    
    def _worker_loop(self) -> None:
        """Worker per radar (polling continuo)"""
        logger.info("📡 Radar worker loop started")
        
        last_presence = False
        
        while self.running:
            try:
                data = self._read_radar_data()
                
                if data:
                    # Invia evento solo se presenza cambia
                    current_presence = data['presence']
                    
                    if current_presence != last_presence:
                        # Log con info dettagliate inclusi energy levels
                        logger.info(
                            f"📡 Radar: Presence={current_presence} | "
                            f"Distance={data['distance']}cm | "
                            f"Movement Energy={data['mov_energy']} | "
                            f"Static Energy={data['static_energy']}"
                        )
                        
                        event = create_input_event(
                            InputEventType.SENSOR_PRESENCE,
                            current_presence,
                            source="radar",
                            priority=EventPriority.LOW,
                            metadata=data
                        )
                        
                        self.input_queue.put(event)
                        last_presence = current_presence
                    
                    # Invia evento movimento se rilevato (con threshold energia)
                    if data.get('movement') and data['mov_energy'] > 15:  # Filtra rumore
                        logger.debug(
                            f"🏃 Movement detected: distance={data['mov_distance']}cm, "
                            f"energy={data['mov_energy']}"
                        )
                        event = create_input_event(
                            InputEventType.SENSOR_MOVEMENT,
                            True,
                            source="radar",
                            priority=EventPriority.LOW,
                            metadata=data
                        )
                        self.input_queue.put(event)
                
                time.sleep(self.interval)
            
            except KeyboardInterrupt:
                logger.info("Radar worker interrupted by user")
                break
            except Exception as e:
                logger.error(f"Radar worker error: {e}", exc_info=True)
                time.sleep(1.0)  # Backoff prima di retry
    
    def _read_radar_data(self) -> Optional[Dict[str, Any]]:
        """Legge dati dal radar LD2410C"""
        if not self.radar:
            return None
        
        try:
            if self.radar.in_waiting > 0:
                data = self.radar.read(self.radar.in_waiting)
                
                # Cerca header frame: F4 F3 F2 F1
                header = b'\xF4\xF3\xF2\xF1'
                idx = data.find(header)
                
                if idx != -1 and len(data) >= idx + 23:
                    target_state = data[idx + 8]
                    
                    presence = target_state > 0
                    movement = target_state in [1, 3]
                    static = target_state in [2, 3]
                    
                    # Distanze e energie (little endian)
                    mov_distance = data[idx + 9] + (data[idx + 10] << 8)
                    mov_energy = data[idx + 11]
                    static_distance = data[idx + 12] + (data[idx + 13] << 8)
                    static_energy = data[idx + 14]
                    detection_distance = data[idx + 15] + (data[idx + 16] << 8)
                    
                    distance = detection_distance if presence else 0
                    
                    return {
                        'presence': presence,
                        'movement': movement,
                        'static': static,
                        'distance': distance,
                        'mov_distance': mov_distance,
                        'mov_energy': mov_energy,
                        'static_distance': static_distance,
                        'static_energy': static_energy
                    }
        
        except (OSError, IOError) as e:
            # Errori di comunicazione seriale - comuni, non critici
            logger.debug(f"Radar read error (communication): {e}")
        except Exception as e:
            logger.error(
                f"Unexpected radar read error: {e}",
                exc_info=True
            )
        
        return None


class MockRadarInput(InputPort):
    """
    Mock Radar Input per testing.
    Genera dati fake per simulare radar.
    """
    
    def __init__(self, name: str, config: dict, input_queue: PriorityQueue):
        super().__init__(name, config, input_queue)
        
        self.interval = config['interval']
        self.worker_thread: Optional[threading.Thread] = None
        
        logger.info(f"📡 MockRadarInput initialized")
    
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
        
        presence = False
        counter = 0
        
        while self.running:
            try:
                # Toggle presence ogni 3 iterazioni
                if counter % 3 == 0:
                    presence = not presence
                    
                    # Genera valori realistici con energy levels
                    distance = random.randint(50, 250) if presence else 0
                    mov_energy = random.randint(20, 80) if presence else 0
                    static_energy = random.randint(30, 70) if presence else 0
                    
                    logger.info(
                        f"📡 [MOCK] Radar: Presence={presence} | "
                        f"Distance={distance}cm | "
                        f"Mov Energy={mov_energy} | "
                        f"Static Energy={static_energy}"
                    )
                    
                    event = create_input_event(
                        InputEventType.SENSOR_PRESENCE,
                        presence,
                        source="mock_radar",
                        priority=EventPriority.LOW,
                        metadata={
                            'presence': presence,
                            'movement': presence,
                            'static': presence,
                            'distance': distance,
                            'mov_distance': distance - 10 if presence else 0,
                            'mov_energy': mov_energy,
                            'static_distance': distance if presence else 0,
                            'static_energy': static_energy
                        }
                    )
                    self.input_queue.put(event)
                
                counter += 1
            
            except Exception as e:
                logger.error(f"Mock radar error: {e}")
            
            time.sleep(self.interval)
