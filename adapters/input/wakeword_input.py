import threading
import queue
import time
import os
import logging
from pathlib import Path
import pvporcupine
from pvrecorder import PvRecorder
from adapters.ports import InputPort
from adapters.shared_audio_state import SuppressStream, find_jabra_pvrecorder
from core.events import InputEventType, Event, EventPriority
from core.commands import AdapterCommand

logger = logging.getLogger(__name__)


class WakewordInput(InputPort):
    """
    Input adapter for wake word detection using Porcupine.
    Dedicated to handling wake word events and pushing them to the input queue.
    """
    def __init__(self, name: str, config: dict, input_queue: queue.PriorityQueue, interrupt_queue: queue.Queue):
        super().__init__(name=name, config=config, input_queue=input_queue, interrupt_queue=interrupt_queue)
        self._thread = None
        self._running = False
        self._paused = False  # NEW: stato pausa
        self._porcupine = None
        self._recorder = None  # Track recorder instance
        self._recorder_lock = threading.Lock()  # Proteggi accesso al recorder
        
        # Risolvi path wakeword (relativo a BUDDY_HOME)
        wakeword_path = config['wakeword']  # Fail-fast: must be present
        buddy_home = Path(os.getenv('BUDDY_HOME', '.')).resolve()
        wakeword_file = Path(wakeword_path)
        
        # Se relativo, risolvilo rispetto a BUDDY_HOME
        if not wakeword_file.is_absolute():
            wakeword_file = buddy_home / wakeword_file
        
        # Fail-fast: file deve esistere
        if not wakeword_file.exists():
            raise FileNotFoundError(
                f"Wake word file not found: {wakeword_file} (from config: {wakeword_path})"
            )
        
        self._wakeword: str = str(wakeword_file.resolve())
        logger.info(f"✅ Wake word file: {self._wakeword}")
        
        # Sensitivity (0.0 - 1.0, default: 0.5)
        self._sensitivity: float = config['sensitivity'] # Fail-fast: must be present
        if not 0.0 <= self._sensitivity <= 1.0:
            raise ValueError(f"Sensitivity must be between 0.0 and 1.0, got: {self._sensitivity}")
        logger.info(f"✅ Wake word sensitivity: {self._sensitivity}")
        
        # Access key da variabile di ambiente (fail-fast)
        access_key = os.getenv("PICOVOICE_ACCESS_KEY")
        if not access_key:
            raise RuntimeError("PICOVOICE_ACCESS_KEY environment variable not set")
        self._access_key: str = access_key
        
        # Auto-detect Jabra device
        device_index = find_jabra_pvrecorder()
        if device_index is None:
            raise RuntimeError("Jabra device not found for WakewordInput")
        self._device_index: int = device_index  # Type narrowing: guaranteed non-None after check
        logger.info(f"✅ Jabra auto-detected for WakewordInput: PvRecorder index={self._device_index}")

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("WakewordInput already running")
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        # The recorder will be cleaned up in the finally block of _run()
        # Wait for thread to exit cleanly
        if self._thread is not None:
            self._thread.join(timeout=2)

    
    def supported_commands(self):
        """Dichiara comandi supportati"""
        return {
            AdapterCommand.WAKEWORD_LISTEN_START,
            AdapterCommand.WAKEWORD_LISTEN_STOP
        }
    
    def handle_command(self, command: AdapterCommand) -> bool:
        """
        Gestisce comandi di controllo dal Brain.
        
        Args:
            command: Comando da eseguire
            
        Returns:
            True se gestito, False se ignorato
        """
        if command == AdapterCommand.WAKEWORD_LISTEN_STOP:
            self._paused = True
            # Ferma e rilascia il recorder per liberare il dispositivo
            with self._recorder_lock:
                if self._recorder is not None:
                    try:
                        self._recorder.stop()
                        self._recorder.delete()
                        self._recorder = None
                        logger.info("🔇 PvRecorder stopped and released")
                    except Exception as e:
                        logger.error(f"Error stopping recorder: {e}")
            return True
        elif command == AdapterCommand.WAKEWORD_LISTEN_START:
            self._paused = False
            # Il recorder verrà ricreato nel loop
            return True
        return False

    def _run(self):
        self._porcupine = pvporcupine.create(
            access_key=self._access_key,
            keyword_paths=[self._wakeword],
            sensitivities=[self._sensitivity]
        )
        
        try:
            while self._running:
                # Se in pausa, aspetta senza tenere il recorder attivo
                if self._paused:
                    # Assicurati che il recorder sia fermo (con lock)
                    with self._recorder_lock:
                        if self._recorder is not None:
                            try:
                                self._recorder.stop()
                                self._recorder.delete()
                                self._recorder = None
                            except Exception as e:
                                logger.error(f"Error cleaning recorder during pause: {e}")
                    time.sleep(0.1)
                    continue
                
                # Crea/ricrea recorder se necessario (con lock)
                with self._recorder_lock:
                    if self._recorder is None:
                        # Sopprimi stderr per evitare ALSA warnings
                        with SuppressStream():
                            self._recorder = PvRecorder(
                                device_index=self._device_index,
                                frame_length=self._porcupine.frame_length
                            )
                            self._recorder.start()
                        logger.info("🎤 PvRecorder started for wake word detection")
                
                try:
                    # Leggi con lock per evitare race condition
                    with self._recorder_lock:
                        if self._recorder is not None:
                            pcm = self._recorder.read()
                        else:
                            # Recorder fermato da handle_command, skip
                            time.sleep(0.01)
                            continue
                    
                    result = self._porcupine.process(pcm)
                    if result >= 0:
                        event = Event(
                            type=InputEventType.WAKEWORD,
                            content='wakeword_detected',
                            priority=EventPriority.HIGH,
                            metadata={'wakeword': self._wakeword}
                        )
                        self.input_queue.put(event)
                except (OSError, IOError) as e:
                    # Stream closed by stop() - exit cleanly
                    if not self._running:
                        break
                    # Altrimenti, ricrea recorder al prossimo giro
                    with self._recorder_lock:
                        if self._recorder is not None:
                            try:
                                self._recorder.stop()
                                self._recorder.delete()
                            except:
                                pass
                            self._recorder = None
        finally:
            # Cleanup (con lock)
            with self._recorder_lock:
                if self._recorder is not None:
                    try:
                        self._recorder.stop()
                        self._recorder.delete()
                    except Exception as e:
                        logger.error(f"Error cleaning up recorder: {e}")
            if self._porcupine is not None:
                self._porcupine.delete()
