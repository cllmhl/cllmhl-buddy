import logging
import threading
import time
import os
from queue import Empty
from typing import List, Dict, Optional

from PyP100 import PyL530

from adapters.ports import OutputPort
from core.events import OutputEventType, OutputEvent

logger = logging.getLogger(__name__)

class TapoOutput(OutputPort):
    """
    Output Adapter per controllare lampadine TAPO (P100/L530).
    Gestisce accensione e spegnimento di dispositivi specifici.
    """
    
    def __init__(self, name: str, config: dict, queue_maxsize: int = 50):
        super().__init__(name, config, queue_maxsize)
        # Usa variabili d'ambiente per email e password
        self.email = os.environ.get("TAPO_EMAIL")
        self.password = os.environ.get("TAPO_PASSWORD")
        self.devices_config = config.get("devices", {})  # mappa: nome_logico -> ip
        self.devices: Dict[str, PyL530.L530] = {}
        self._thread: Optional[threading.Thread] = None
        
    def _get_or_create_device(self, device_name: str) -> Optional[PyL530.L530]:
        """Recupera o inizializza un dispositivo TAPO."""
        if device_name in self.devices:
            return self.devices[device_name]
            
        ip = self.devices_config.get(device_name)
            
        try:
            if not self.email or not self.password:
                logger.error(f"❌ TAPO Credentials missing for '{device_name}'. Check TAPO_EMAIL/TAPO_PASSWORD env vars.")
                return None

            # Usa PyL530 per lampadine L530
            device = PyL530.L530(ip, self.email, self.password)
            
            logger.debug(f"🤝 Handshaking with {device_name} ({ip})...")
            device.handshake()
            
            logger.debug(f"🔑 Logging in to {device_name} ({ip})...")
            device.login()
            
            self.devices[device_name] = device
            logger.debug(f"✅ Connesso a TAPO device '{device_name}' ({ip})")
            return device
            
        except KeyError as e:
            if 'result' in str(e):
                logger.error(f"❌ TAPO Protocol Error on '{device_name}' ({ip}): Response missing 'result'. Likely authentication failed or firmware incompatibility.")
            else:
                logger.error(f"❌ TAPO KeyError on '{device_name}' ({ip}): {e}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Errore connessione TAPO device '{device_name}' ({ip}): {e}", exc_info=True)
            return None

    def start(self) -> None:
        """Avvia il worker thread per processare gli eventi."""
        if self.running:
            return
            
        self.running = True
        self._thread = threading.Thread(target=self._worker, name=f"{self.name}_worker", daemon=True)
        self._thread.start()
        logger.info(f"✅ {self.name} started")

    def stop(self) -> None:
        """Ferma il worker."""
        self.running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info(f"🛑 {self.name} stopped")

    @classmethod
    def handled_events(cls) -> List[OutputEventType]:
        return [
            OutputEventType.LIGHT_ON,
            OutputEventType.LIGHT_OFF
        ]

    def _worker(self):
        """Loop principale che consuma eventi dalla coda."""
        while self.running:
            try:
                event: OutputEvent = self.output_queue.get(timeout=1.0)
                self._process_event(event)
                self.output_queue.task_done()
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error in TapoOutput worker: {e}", exc_info=True)

    def _process_event(self, event: OutputEvent):
        """Esegue l'azione richiesta dall'evento."""
        logger.info(f"💡 Processing TAPO event: {event.type.name} content={event.content}")
        
        target = str(event.content).lower() if event.content else "tutto"
        
        try:
            if event.type == OutputEventType.LIGHT_ON:
                if target == "tutto":
                    self._control_device("stanza", True)
                    self._control_device("ingresso", True)
                elif target in ["stanza", "ingresso"]:
                    self._control_device(target, True)
                else:
                    logger.warning(f"Unknown target for LIGHT_ON: {target}")

            elif event.type == OutputEventType.LIGHT_OFF:
                if target == "tutto":
                     self._control_device("stanza", False)
                     self._control_device("ingresso", False)
                elif target in ["stanza", "ingresso"]:
                     self._control_device(target, False)
                else:
                     logger.warning(f"Unknown target for LIGHT_OFF: {target}")
                     
        except Exception as e:
            logger.error(f"Error processing TAPO event {event.type.name}: {e}")

    def _control_device(self, device_key: str, state: bool):
        """Accende o spegne un dispositivo gestendo la riconnessione."""
        device = self._get_or_create_device(device_key)
        if not device:
            return

        try:
            if state:
                device.turnOn()
                logger.info(f"💡 TAPO: {device_key} ACCESA")
            else:
                device.turnOff()
                logger.info(f"🌑 TAPO: {device_key} SPENTA")
        except Exception as e:
            logger.warning(f"⚠️ Errore comando TAPO su '{device_key}': {e}. Tento riconnessione...")
            # Rimuovi cache e riprova una volta
            if device_key in self.devices:
                del self.devices[device_key]
            
            # Retry
            device = self._get_or_create_device(device_key)
            if device:
                try:
                    if state:
                        device.turnOn()
                    else:
                        device.turnOff()
                    logger.info(f"💡 TAPO: {device_key} comando riuscito dopo riconnessione")
                except Exception as retry_err:
                     logger.error(f"❌ TAPO: Fallito anche dopo riconnessione: {retry_err}")
