import threading
import queue
import time
import os
import logging
import pvporcupine
import pyaudio
from adapters.ports import InputPort
from core.events import InputEventType, Event, EventPriority
from core.commands import AdapterCommand

logger = logging.getLogger(__name__)


class WakewordInput(InputPort):
    """
    Input adapter for wake word detection using Porcupine.
    Dedicated to handling wake word events and pushing them to the input queue.
    """
    def __init__(self, config: dict, input_queue: queue.PriorityQueue):
        super().__init__(name="wakeword_input", config=config, input_queue=input_queue)
        self._thread = None
        self._running = False
        self._paused = False  # NEW: stato pausa
        self._porcupine = None
        self._audio_stream = None
        self._wakeword = config['wakeword']  # Fail-fast: must be present
        
        # Access key da variabile di ambiente (fail-fast)
        access_key = os.getenv("PICOVOICE_ACCESS_KEY")
        if not access_key:
            raise RuntimeError("PICOVOICE_ACCESS_KEY environment variable not set")
        self._access_key: str = access_key
        
        # Auto-detect Jabra device
        from adapters.audio_device_manager import find_jabra_pvrecorder
        self._device_index = find_jabra_pvrecorder()
        if self._device_index is None:
            raise RuntimeError("Jabra device not found for WakewordInput")
        logger.info(f"✅ Jabra auto-detected for WakewordInput: PvRecorder index={self._device_index}")

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("WakewordInput already running")
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        # Close audio stream FIRST to unblock the read() call
        if self._audio_stream is not None:
            self._audio_stream.close()
            self._audio_stream = None
        # Now the thread can exit cleanly
        if self._thread is not None:
            self._thread.join(timeout=2)
        # Clean up Porcupine
        if self._porcupine is not None:
            self._porcupine.delete()
            self._porcupine = None
    
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
            return True
        elif command == AdapterCommand.WAKEWORD_LISTEN_START:
            self._paused = False
            return True
        return False

    def _run(self):
        self._porcupine = pvporcupine.create(
            access_key=self._access_key,
            keyword_paths=[self._wakeword]
        )
        pa = pyaudio.PyAudio()
        self._audio_stream = pa.open(
            rate=self._porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=self._porcupine.frame_length,
            input_device_index=self._device_index
        )
        while self._running:
            # Se in pausa, aspetta senza consumare CPU
            if self._paused:
                time.sleep(0.1)
                continue
            
            try:
                pcm = self._audio_stream.read(self._porcupine.frame_length, exception_on_overflow=False)
                pcm = memoryview(pcm).cast('h')
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
                raise  # Re-raise if it's an unexpected error
        
        # Cleanup (only if not already done by stop())
        if self._audio_stream is not None:
            self._audio_stream.close()
        if self._porcupine is not None:
            self._porcupine.delete()
