"""
Door Input Adapter - Door sensor via MQTT
"""

import logging
import threading
import json
import paho.mqtt.client as mqtt
from queue import PriorityQueue

from adapters.ports import InputPort
from core.events import create_input_event, InputEventType, EventPriority
from core.state import global_state

logger = logging.getLogger(__name__)


class DoorInput(InputPort):
    """
    Door Input Adapter.
    Rileva lo stato della porta (aperta/chiusa) tramite sensore via MQTT.
    """
    
    def __init__(self, name: str, config: dict, input_queue: PriorityQueue):
        super().__init__(name, config, input_queue)
        
        # Configurazione MQTT
        self.broker = config['broker']
        self.topic = config['topic']
        
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.worker_thread = None
        
        # Stato locale per evitare eventi doppi
        self.last_state = None
        
        logger.info(
            f"🚪 DoorInput initialized "
            f"(broker: {self.broker}, topic: {self.topic})"
        )
    
    def _on_connect(self, client, userdata, flags, rc):
        logger.info(f"✅ DoorInput connesso alla rete ZigBee (Broker MQTT)!")
        client.subscribe(self.topic)
        
    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            if "contact" in payload:
                is_closed = payload["contact"] == True
                
                # Invia l'evento solo se c'è un reale cambio di stato
                if self.last_state != is_closed:
                    self.last_state = is_closed
                    
                    # Aggiorna lo stato globale
                    global_state.is_door_closed = is_closed
                    
                    door_event = create_input_event(
                        InputEventType.SENSOR_DOOR,
                        is_closed,
                        source=self.name,
                        priority=EventPriority.NORMAL,
                        metadata={
                            'battery': payload.get('battery', 'N/A')
                        }
                    )
                    self.input_queue.put(door_event)
                    
                    if is_closed:
                        logger.debug("🚪 STATO: La porta è CHIUSA 🟢")
                    else:
                        logger.debug("🚨 STATO: La porta è APERTA 🔴")
        except Exception as e:
            logger.error(f"Errore parsing messaggio MQTT da {self.topic}: {e}")

    def start(self) -> None:
        """Avvia worker thread"""
        self.running = True
        
        try:
            self.client.connect(self.broker, 1883, 60)
            self.worker_thread = threading.Thread(
                target=self._worker_loop,
                daemon=True,
                name=f"{self.name}_door"
            )
            self.worker_thread.start()
            logger.info("▶️  Door worker started")
        except Exception as e:
            logger.error(f"⚠️ Errore connessione broker MQTT {self.broker}: {e}")
        
        logger.info(f"▶️  {self.name} started")
    
    def stop(self) -> None:
        """Ferma worker thread"""
        logger.info(f"⏸️  Stopping {self.name}...")
        self.running = False
        
        self.client.disconnect()
        
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=3.0)
            if self.worker_thread.is_alive():
                logger.warning(f"⚠️  {self.name} thread did not terminate")
        
        logger.info(f"⏹️  {self.name} stopped")
    
    def _worker_loop(self) -> None:
        """Worker per loop MQTT"""
        logger.info("🚪 Door worker loop started")
        self.client.loop_forever()
