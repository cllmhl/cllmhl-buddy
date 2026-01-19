import threading
import queue
from adapters.ports import InputPort
from core.events import InputEventType, Event, EventPriority

class WakewordInput(InputPort):
    """
    Input adapter for wake word detection using Porcupine.
    Dedicated to handling wake word events and pushing them to the input queue.
    """
    def __init__(self, config: dict, input_queue: queue.PriorityQueue):
        super().__init__(name="wakeword_input", config=config, input_queue=input_queue)
        self._thread = None
        self._running = False
        self._porcupine = None
        self._audio_stream = None
        self._wakeword = config['wakeword']  # Fail-fast: must be present
        self._access_key = config['access_key']  # Fail-fast: must be present
        self._device_index = config.get('device_index', 0)

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

    def _run(self):
        try:
            import pvporcupine
            import pyaudio
        except ImportError as e:
            raise ImportError("Porcupine and PyAudio must be installed: {}".format(e))

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
