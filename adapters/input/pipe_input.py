"""
Pipe Input Adapter - Legge eventi da named pipe
Permette comunicazione con buddy tramite IPC (Inter-Process Communication)
"""

import os
import json
import threading
import logging
from pathlib import Path
from typing import Optional

from core.events import Event, InputEventType, OutputEventType, EventPriority, create_output_event
from adapters.ports import InputPort


logger = logging.getLogger(__name__)


class PipeInputAdapter(InputPort):
    """
    Input adapter che legge eventi da una named pipe (FIFO).
    Formato: JSON line-delimited
    
    Eventi supportati:
    - DIRECT_OUTPUT: wrapper per inviare OutputEvents direttamente
    - Altri InputEvents standard
    
    Esempio JSON:
    {
        "type": "direct_output",
        "content": {
            "event_type": "speak",
            "content": "Hello!",
            "priority": "high"
        }
    }
    """
    
    def __init__(self, name: str, config: dict, input_queue):
        """
        Args:
            name: Nome adapter
            config: Configurazione con 'pipe_path' (default: data/buddy.in)
            input_queue: Queue per pubblicare eventi
        """
        super().__init__(name, config, input_queue)
        self.pipe_path = Path(config['pipe_path'])
        self._thread: Optional[threading.Thread] = None
        
    def start(self):
        """Avvia il reader thread"""
        if self.running:
            logger.warning("PipeInput già in esecuzione")
            return
            
        # Crea directory se non esiste
        self.pipe_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Crea named pipe se non esiste
        if not self.pipe_path.exists():
            try:
                os.mkfifo(self.pipe_path)
                logger.info(f"Named pipe creata: {self.pipe_path}")
            except OSError as e:
                logger.error(f"Errore creazione named pipe: {e}")
                return
        elif not self._is_fifo(self.pipe_path):
            logger.error(f"{self.pipe_path} esiste ma non è una named pipe")
            return
            
        self.running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        logger.info(f"PipeInput avviato su {self.pipe_path}")
        
    def stop(self):
        """Ferma il reader thread"""
        if not self.running:
            return
        
        logger.info(f"⏸️  Stopping {self.name}...")
        self.running = False
        
        # Sblocca la read aprendo la pipe in scrittura
        try:
            with open(self.pipe_path, 'w') as f:
                f.write('\n')
        except:
            pass
        
        # Aspetta thread con timeout
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
            if self._thread.is_alive():
                logger.warning(f"⚠️  {self.name} thread did not terminate")
            
        logger.info(f"⏹️  {self.name} stopped")
        
    def _is_fifo(self, path: Path) -> bool:
        """Verifica se il path è una named pipe"""
        import stat
        return stat.S_ISFIFO(os.stat(path).st_mode)
        
    def _read_loop(self):
        """Loop di lettura dalla pipe"""
        while self.running:
            try:
                # Apri in read mode (blocca finché qualcuno scrive)
                with open(self.pipe_path, 'r') as pipe:
                    logger.debug("Pipe aperta, in attesa di dati...")
                    
                    while self.running:
                        line = pipe.readline()
                        if not line:  # EOF
                            break
                            
                        line = line.strip()
                        if not line:
                            continue
                            
                        try:
                            self._process_line(line)
                        except Exception as e:
                            logger.error(f"Errore processing line: {e}", exc_info=True)
                            
            except Exception as e:
                if self.running:
                    logger.error(f"Errore lettura pipe: {e}", exc_info=True)
                    
    def _process_line(self, line: str):
        """
        Processa una linea JSON dalla pipe
        
        Formato atteso:
        {
            "type": "direct_output" | "user_speech" | ...,
            "content": <any>,
            "priority": "normal" | "high" | "low" | "critical",
            "metadata": {...}
        }
        """
        data = json.loads(line)
        
        event_type_str = data.get("type")
        content = data.get("content")
        priority_str = data.get("priority", "normal").upper()
        metadata = data.get("metadata", {})
        
        # Parse priority
        try:
            priority = EventPriority[priority_str]
        except KeyError:
            priority = EventPriority.NORMAL
            logger.warning(f"Priorità sconosciuta: {priority_str}, uso NORMAL")
            
        # Gestisci DIRECT_OUTPUT in modo speciale
        if event_type_str == "direct_output":
            # metadata può essere sia nel top-level che nel content
            output_metadata = data.get("metadata", {})
            output_event = self._parse_direct_output(content, priority, output_metadata)
            if output_event:
                # Crea un InputEvent wrapper
                event = Event(
                    priority=priority,
                    type=InputEventType.DIRECT_OUTPUT,
                    content=output_event,
                    source=self.name,
                    metadata=metadata
                )
                self.input_queue.put(event)
                logger.info(f"DIRECT_OUTPUT event pubblicato: {output_event.type.value}")
            return
            
        # Altri InputEvents
        try:
            event_type = InputEventType[event_type_str.upper()]
            event = Event(
                priority=priority,
                type=event_type,
                content=content,
                source=self.name,
                metadata=metadata
            )
            self.input_queue.put(event)
            logger.info(f"Event pubblicato: {event_type.value}")
            
        except KeyError:
            logger.error(f"Tipo evento sconosciuto: {event_type_str}")
            
    def _parse_direct_output(self, content: dict, priority: EventPriority, metadata: Optional[dict] = None) -> Optional[Event]:
        """
        Parsa il content di un DIRECT_OUTPUT event
        
        Formato:
        {
            "event_type": "speak" | "led_control" | ...,
            "content": <any>,
            "priority": "normal" (opzionale, override)
        }
        
        metadata opzionale può contenere dati extra (es: per led_control)
        """
        if not isinstance(content, dict):
            logger.error(f"❌ DIRECT_OUTPUT content deve essere dict, ricevuto: {type(content)}")
            raise TypeError(f"DIRECT_OUTPUT content must be dict, got {type(content)}")
            
        event_type_str = content.get("event_type")
        if not event_type_str:
            logger.error("❌ DIRECT_OUTPUT content manca 'event_type'")
            raise ValueError("DIRECT_OUTPUT content missing required 'event_type' field")
        
        event_content = content.get("content")
        event_priority_str = content.get("priority", priority.name).upper()
        
        try:
            event_type = OutputEventType[event_type_str.upper()]
            event_priority = EventPriority[event_priority_str]
        except KeyError as e:
            logger.error(f"❌ Invalid event_type or priority: {e}", exc_info=True)
            valid_types = [et.name for et in OutputEventType]
            raise ValueError(f"Invalid DIRECT_OUTPUT params. Valid types: {valid_types}") from e
        
        return create_output_event(
            event_type=event_type,
            content=event_content,
            priority=event_priority,
            metadata=metadata or {}
        )
