"""
Radar Input Adapter - Radar LD2410C presence/movement detection
"""

import logging
import threading
import time
import serial
from queue import PriorityQueue, Queue
from typing import Optional, Dict, Any

from adapters.ports import InputPort
from core.events import create_input_event, InputEventType, EventPriority

logger = logging.getLogger(__name__)


class RadarInput(InputPort):
    """
    Radar LD2410C Input Adapter.
    Rileva presenza e movimento tramite radar UART.
    """
    
    def __init__(self, name: str, config: dict, input_queue: PriorityQueue, interrupt_queue: Queue):
        super().__init__(name, config, input_queue, interrupt_queue)
        
        # Configurazione radar
        self.port = config['port']
        self.baudrate = config['baudrate']
        self.interval = config['interval']
        self.sensitivity = config['sensitivity']
        self.confirmations = config['confirmations']
        
        # Hardware
        self.radar = None
        self.worker_thread = None
        
        # Setup radar
        self._setup_radar()
        
        logger.info(
            f"📡 RadarInput initialized "
            f"(port: {self.port}, baudrate: {self.baudrate})"
        )
    
    def _configure_radar(self) -> None:
        """
        Invia comandi di configurazione al radar per aumentare la sensibilità.
        Questo lo rende "più intelligente" nel rilevare persone ferme.
        """
        if not self.radar:
            return

        try:
            logger.info(f"📡 Configuring radar with sensitivity level: {self.sensitivity}...")

            # Valida il valore di sensibilità
            if self.sensitivity not in [1, 2, 3]:
                logger.warning(f"Invalid sensitivity value {self.sensitivity}. Must be 1, 2, or 3. Defaulting to 3.")
                self.sensitivity = 3
            
            # Comandi in formato esadecimale (raw bytes)
            enter_config_cmd = bytes.fromhex("FDFCFBFA0200FF0004030201")
            
            # Costruisci il comando di sensibilità dinamicamente
            sensitivity_hex = f"0{self.sensitivity}"
            set_sensitivity_cmd_str = f"FDFCFBFA04006000{sensitivity_hex}0004030201"
            set_sensitivity_cmd = bytes.fromhex(set_sensitivity_cmd_str)
            
            exit_config_cmd = bytes.fromhex("FDFCFBFA0200FE0004030201")

            # Entra in modalità configurazione
            self.radar.write(enter_config_cmd)
            time.sleep(0.1)
            if self.radar.in_waiting > 0: logger.debug(f"Enter config ACK: {self.radar.read(self.radar.in_waiting).hex()}")

            # Imposta la sensibilità
            self.radar.write(set_sensitivity_cmd)
            time.sleep(0.1)
            if self.radar.in_waiting > 0: logger.debug(f"Set sensitivity ACK: {self.radar.read(self.radar.in_waiting).hex()}")

            # Esci dalla modalità configurazione
            self.radar.write(exit_config_cmd)
            time.sleep(0.1)
            if self.radar.in_waiting > 0: logger.debug(f"Exit config ACK: {self.radar.read(self.radar.in_waiting).hex()}")

            self.radar.reset_input_buffer()
            logger.info(f"✅ Radar sensitivity configured to level {self.sensitivity}.")

        except Exception as e:
            logger.error(f"Failed to configure radar: {e}", exc_info=True)

    def _setup_radar(self) -> None:
        """Setup Radar LD2410C"""
        try:
            self.radar = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1.0
            )
            logger.info(f"✅ Radar connected: {self.port} @ {self.baudrate}")
            self._configure_radar()
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
        """
        Worker per radar con logica di debouncing per stabilizzare il segnale.
        Un cambio di stato (presenza/assenza) viene confermato solo se
        il nuovo stato viene letto per un numero consecutivo di volte
        pari a `self.confirmations`.
        """
        logger.info(f"📡 Radar worker loop started (confirmations: {self.confirmations})")
        
        last_stable_presence = None # Ultimo stato confermato
        potential_presence = None   # Stato potenziale in attesa di conferma
        confirmation_count = 0      # Conteggio conferme consecutive

        while self.running:
            try:
                data = self._read_radar_data()
                
                if data:
                    current_presence = data['presence']

                    # Inizializzazione al primo ciclo
                    if last_stable_presence is None:
                        last_stable_presence = current_presence
                        potential_presence = current_presence
                        confirmation_count = 1
                        logger.info(f"📡 Radar initialized with state: Presence={last_stable_presence}")
                        # Invia subito il primo stato rilevato
                        self._send_presence_event(current_presence, data)


                    # Logica di debouncing
                    if current_presence == potential_presence:
                        confirmation_count += 1
                        logger.debug(f"Confirmation count for state {potential_presence} is now {confirmation_count}")
                    else:
                        # Lo stato è cambiato, resetta il conteggio
                        potential_presence = current_presence
                        confirmation_count = 1
                        logger.debug(f"Potential state changed to {potential_presence}. Resetting count.")

                    # Controlla se il cambio di stato è confermato
                    if confirmation_count >= self.confirmations and potential_presence != last_stable_presence:
                        logger.info(f"✅ State change confirmed: {last_stable_presence} -> {potential_presence} after {self.confirmations} checks.")
                        last_stable_presence = potential_presence
                        if last_stable_presence is not None:
                            self._send_presence_event(last_stable_presence, data)
                    
                    # Gestione evento movimento (indipendente dal debouncing di presenza)
                    if data.get('movement') and data['mov_energy'] > 15:
                        self._send_movement_event(data)
                
                time.sleep(self.interval)
            
            except KeyboardInterrupt:
                logger.info("Radar worker interrupted by user")
                break
            except Exception as e:
                logger.error(f"Radar worker error: {e}", exc_info=True)
                time.sleep(1.0)
    
    def _send_presence_event(self, presence: bool, data: Dict[str, Any]):
        """Invia un evento di presenza al cervello."""
        logger.info(
            f"📡 Radar Event: Presence={presence} | "
            f"Distance={data['distance']}cm | "
            f"Movement Energy={data['mov_energy']} | "
            f"Static Energy={data['static_energy']}"
        )
        event = create_input_event(
            InputEventType.SENSOR_PRESENCE,
            presence,
            source="radar",
            priority=EventPriority.LOW,
            metadata=data
        )
        self.input_queue.put(event)

    def _send_movement_event(self, data: Dict[str, Any]):
        """Invia un evento di movimento al cervello."""
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