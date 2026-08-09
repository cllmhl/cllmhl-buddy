import threading
import queue
import time
import os
import logging
from pathlib import Path
import pyaudio
import numpy as np
import openwakeword
from openwakeword.model import Model
from adapters.ports import InputPort
from adapters.audio_utils import SuppressStream, find_jabra_pyaudio
from core.events import InputEventType, InputEvent, EventPriority
from core.commands import AdapterCommand

logger = logging.getLogger(__name__)

class WakewordInput(InputPort):
    """
    Input adapter for wake word detection using OpenWakeWord.
    Dedicated to handling wake word events and pushing them to the input queue.
    """
    def __init__(self, name: str, config: dict, input_queue: queue.PriorityQueue):
        super().__init__(name=name, config=config, input_queue=input_queue)
        self._thread = None
        self._running = False
        self._paused = False  # NEW: stato pausa
        self._oww_model = None
        self._audio = None
        self._stream = None  # Track stream instance (sostituisce recorder)
        self._stream_lock = threading.Lock()  # Proteggi accesso allo stream (sostituisce recorder_lock)
        
        # Risolvi path wakeword (relativo a BUDDY_HOME)
        # NOTA: OpenWakeWord accetta sia un path a un file .tflite custom, sia il nome stringa di un modello pre-addestrato (es. "hey_jarvis")
        wakeword_path = config['wakeword']  # Fail-fast: must be present
        buddy_home = Path(os.getenv('BUDDY_HOME', '.')).resolve()
        
        # Gestione ibrida: se è un file che finisce in .tflite, prova a risolverlo
        if str(wakeword_path).endswith('.tflite'):
            wakeword_file = Path(wakeword_path)
            # Se relativo, risolvilo rispetto a BUDDY_HOME
            if not wakeword_file.is_absolute():
                wakeword_file = buddy_home / wakeword_file
            
            # Fail-fast: file deve esistere se stiamo usando un path fisico
            if not wakeword_file.exists():
                raise FileNotFoundError(
                    f"Wake word file not found: {wakeword_file} (from config: {wakeword_path})"
                )
            self._wakeword: str = str(wakeword_file.resolve())
            logger.info(f"✅ Wake word file: {self._wakeword}")
        else:
            # Assumiamo sia un modello pre-addestrato built-in (es. "alexa")
            self._wakeword: str = wakeword_path
            logger.info(f"✅ Wake word model name: {self._wakeword}")
        
        # Sensitivity / Threshold (0.0 - 1.0, default: 0.5)
        self._sensitivity: float = config.get('sensitivity', 0.5) # Fail-fast: must be present
        if not 0.0 <= self._sensitivity <= 1.0:
            raise ValueError(f"Sensitivity must be between 0.0 and 1.0, got: {self._sensitivity}")
        logger.info(f"✅ Wake word sensitivity (threshold): {self._sensitivity}")
        
        # Auto-detect Jabra device (mantenuto, se la tua utility find_jabra_pyaudio usa indici validi per PyAudio o ALSA)
        device_index = find_jabra_pyaudio()
        if device_index is None:
            raise RuntimeError("Jabra device not found for WakewordInput")
        self._device_index: int = device_index  # Type narrowing: guaranteed non-None after check
        logger.info(f"✅ Jabra auto-detected for WakewordInput: PyAudio index={self._device_index}")

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
            # Ferma e rilascia il recorder (stream) per liberare il dispositivo
            with self._stream_lock:
                if self._stream is not None:
                    try:
                        self._stream.stop_stream()
                        self._stream.close()
                        self._stream = None
                        logger.info("🔇 Audio stream stopped and released")
                    except Exception as e:
                        logger.error(f"Error stopping stream: {e}")
            return True
        elif command == AdapterCommand.WAKEWORD_LISTEN_START:
            self._paused = False
            # Il recorder (stream) verrà ricreato nel loop
            return True
        return False

    def _run(self):
        try:
            # Crea istanza PyAudio
            self._audio = pyaudio.PyAudio()
            # Crea istanza OpenWakeWord
            self._oww_model = Model(wakeword_model_paths=[self._wakeword])
        except Exception as e:
            logger.error(f"Error initializing OpenWakeWord/PyAudio: {e}")
        try:
            while self._running:
                # Se in pausa, aspetta senza tenere lo stream attivo
                if self._paused:
                    # Assicurati che lo stream sia fermo (con lock)
                    with self._stream_lock:
                        if self._stream is not None:
                            try:
                                self._stream.stop_stream()
                                self._stream.close()
                                self._stream = None
                            except Exception as e:
                                logger.error(f"Error cleaning stream during pause: {e}")
                    time.sleep(0.1)
                    continue
                
                # Crea/ricrea stream se necessario (con lock)
                with self._stream_lock:
                    if self._stream is None:
                        # Sopprimi stderr per evitare ALSA warnings
                        with SuppressStream():
                            self._stream = self._audio.open(
                                format=pyaudio.paInt16,
                                channels=1,
                                rate=16000,
                                input=True,
                                frames_per_buffer=1280,
                                input_device_index=self._device_index
                            )
                        logger.info("🎤 Audio stream started for wake word detection")
                
                try:
                    # Leggi con lock per evitare race condition
                    with self._stream_lock:
                        if self._stream is not None:
                            # Legge esattamente 1280 frame per OpenWakeWord
                            audio_chunk = self._stream.read(1280, exception_on_overflow=False)
                            # Converti in array numpy int16
                            audio_data = np.frombuffer(audio_chunk, dtype=np.int16)
                        else:
                            # Stream fermato da handle_command, skip
                            time.sleep(0.01)
                            continue
                    
                    # Processa l'audio
                    self._oww_model.predict(audio_data)
                    
                    # Controlla le previsioni per tutti i modelli caricati
                    for mdl in self._oww_model.prediction_buffer.keys():
                        # OpenWakeWord restituisce confidenza tra 0.0 e 1.0
                        if self._oww_model.prediction_buffer[mdl][-1] > self._sensitivity:
                            event = InputEvent(
                                type=InputEventType.WAKEWORD,
                                content='wakeword_detected',
                                priority=EventPriority.HIGH,
                                metadata={'wakeword': mdl}
                            )
                            logger.info("🎤 Wake word detected")
                            self.input_queue.put(event)
                            # Pulisce il buffer per evitare rilevamenti multipli ravvicinati
                            self._oww_model.reset() 

                except (OSError, IOError) as e:
                    # Stream closed by stop() - exit cleanly
                    if not self._running:
                        break
                    # Altrimenti, ricrea stream al prossimo giro
                    with self._stream_lock:
                        if self._stream is not None:
                            try:
                                self._stream.stop_stream()
                                self._stream.close()
                            except:
                                pass
                            self._stream = None
        except Exception as e:
            logger.error(f"Error in WakewordInput thread: {e}") 
        finally:
            # Cleanup (con lock)
            with self._stream_lock:
                if self._stream is not None:
                    try:
                        self._stream.stop_stream()
                        self._stream.close()
                    except Exception as e:
                        logger.error(f"Error cleaning up stream: {e}")
            if self._audio is not None:
                self._audio.terminate()