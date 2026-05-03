"""
Luminance Input Adapter - LDR sensor via Arduino Serial
"""

import logging
import threading
import time
import serial
from queue import PriorityQueue

from adapters.ports import InputPort
from core.events import create_input_event, InputEventType, EventPriority
from core.state import global_state

logger = logging.getLogger(__name__)


class LuminanceInput(InputPort):
    """
    LDR Luminance Input Adapter.
    Rileva la luminosità tramite sensore LDR letto via seriale da un Arduino.
    """
    
    def __init__(self, name: str, config: dict, input_queue: PriorityQueue):
        super().__init__(name, config, input_queue)
        
        # Configurazione Seriale
        self.port = config['port']
        self.baud_rate = config['baud_rate']
        self.interval = config['interval']  # Frequenza di invio eventi
        
        # Hardware
        self.ser = None
        self.worker_thread = None
        
        # Stato locale per evitare spam di eventi
        self.last_event_time = 0
        self.last_event_luminance = None
        self.significant_change_threshold = config['threshold']
        
        logger.info(
            f"🔆  LuminanceInput initialized "
            f"(port: {self.port}, baud_rate: {self.baud_rate})"
        )
    
    def _setup_serial(self) -> bool:
        """Setup serial connection"""
        try:
            self.ser = serial.Serial(self.port, self.baud_rate, timeout=1)
            time.sleep(2) # L'Arduino si riavvia all'apertura della seriale
            self.ser.reset_input_buffer()
            logger.info(f"✅ Connesso alla seriale {self.port} per LDR")
            return True
        except serial.SerialException as e:
            logger.error(f"⚠️ Errore connessione seriale LDR su {self.port}: {e}")
            self.ser = None
            return False

    def start(self) -> None:
        """Avvia worker thread"""
        self.running = True
        
        if self._setup_serial():
            self.worker_thread = threading.Thread(
                target=self._worker_loop,
                daemon=True,
                name=f"{self.name}_ldr"
            )
            self.worker_thread.start()
            logger.info("▶️  LDR worker started")
        else:
            logger.warning("⚠️ Seriale LDR non disponibile, worker non avviato")
        
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
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
                logger.debug("Seriale LDR chiusa")
            except Exception as e:
                logger.debug(f"Errore chiusura seriale LDR: {e}")
        
        logger.info(f"⏹️  {self.name} stopped")
    
    def _worker_loop(self) -> None:
        """Worker per lettura seriale continua"""
        logger.info("🔆  LDR worker loop started")

        while self.running:
            try:
                if self.ser and self.ser.in_waiting > 0:
                    linea_dati = self.ser.readline().decode('utf-8').rstrip()
                    
                    if linea_dati.isdigit():
                        luminosita = int(linea_dati)
                        
                        # Il sensore invia ogni 100ms, salviamo sempre lo stato globale
                        global_state.luminance = luminosita
                        
                        current_time = time.time()
                        
                        # Genera evento se è passato l'intervallo O se c'è un cambiamento significativo
                        should_emit = False
                        
                        if current_time - self.last_event_time >= self.interval:
                            should_emit = True
                        elif self.last_event_luminance is not None and abs(luminosita - self.last_event_luminance) >= self.significant_change_threshold:
                            should_emit = True
                            
                        if should_emit:
                            self.last_event_time = current_time
                            self.last_event_luminance = luminosita
                            
                            luminance_event = create_input_event(
                                InputEventType.SENSOR_LUMINANCE,
                                luminosita,
                                source=self.name,
                                priority=EventPriority.LOW,
                                metadata={
                                    'luminance': luminosita,
                                    'unit': 'raw',
                                    'sensor': 'LDR'
                                }
                            )
                            self.input_queue.put(luminance_event)
                            logger.debug(f"🔆  Evento LDR inviato: Lum={luminosita}")
                else:
                    # Piccolo sleep se non ci sono dati per non bloccare la CPU
                    time.sleep(0.01)

            except serial.SerialException as e:
                logger.error(f"Errore lettura seriale LDR: {e}")
                time.sleep(1) # Attesa prima di riprovare (o potremmo tentare la riconnessione)
            except Exception as e:
                logger.error(f"Errore inatteso nel worker LDR: {e}", exc_info=True)
                time.sleep(1)
