"""
Voice Input Adapters - Wake Word + Speech Recognition
"""

import os
import time
import logging
import threading
from queue import PriorityQueue
from typing import Optional

import speech_recognition as sr

# Picovoice imports (opzionali)
try:
    import pvporcupine
    from pvrecorder import PvRecorder
    PICOVOICE_AVAILABLE = True
except ImportError:
    PICOVOICE_AVAILABLE = False
    logging.warning("⚠️ Picovoice not available. Wake word disabled.")

# Mock GPIO per testing
if not os.path.exists('/proc/device-tree/model'):
    os.environ['GPIOZERO_PIN_FACTORY'] = 'mock'

from gpiozero import LED

from adapters.ports import VoiceInputPort
from adapters.audio_device_manager import get_jabra_manager
from core.events import create_input_event, EventType, EventPriority

logger = logging.getLogger(__name__)


class SuppressStream:
    """Sopprime stderr temporaneamente"""
    def __enter__(self):
        self.err_null = os.open(os.devnull, os.O_WRONLY)
        self.old_err = os.dup(2)
        os.dup2(self.err_null, 2)
    
    def __exit__(self, *args):
        os.dup2(self.old_err, 2)
        os.close(self.err_null)
        os.close(self.old_err)


class JabraVoiceInput(VoiceInputPort):
    """
    Voice Input con Jabra + Porcupine Wake Word.
    Gestisce riconoscimento wake word e speech-to-text.
    Usa AudioDeviceManager per coordinamento con output.
    """
    
    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        
        # Configurazione
        self.stt_mode = config.get('stt_mode', 'cloud').lower()
        self.wake_word_path = config.get('wake_word_path')
        
        # Device Manager per coordinamento
        self.device_manager = get_jabra_manager()
        
        # LED ascolto (GPIO 26)
        self.led_pin = config.get('led_ascolto_pin', 26)
        try:
            self.led_ascolto = LED(self.led_pin)
            logger.info(f"✅ LED listening on GPIO {self.led_pin}")
        except Exception as e:
            logger.warning(f"⚠️ LED init failed: {e}")
            self.led_ascolto = None
        
        # Porcupine/Recorder
        self.porcupine = None
        self.recorder = None
        self.device_index = -1
        self.enabled = False
        
        # Thread worker
        self.worker_thread = None
        
        # Setup hardware
        self._setup_hardware()
        
        if self.enabled:
            logger.info(f"🎤 JabraVoiceInput initialized (wake word enabled)")
        else:
            logger.warning(f"⚠️ JabraVoiceInput initialized (wake word DISABLED)")
    
    def _setup_hardware(self) -> None:
        """Setup Porcupine + PvRecorder"""
        if not PICOVOICE_AVAILABLE:
            logger.warning("⚠️ Picovoice not available")
            return
        
        # Check access key
        access_key = os.getenv("PICOVOICE_ACCESS_KEY")
        if not access_key:
            logger.warning("⚠️ PICOVOICE_ACCESS_KEY not found")
            return
        
        # Check wake word file
        if not self.wake_word_path or not os.path.exists(self.wake_word_path):
            logger.warning(f"⚠️ Wake word file not found: {self.wake_word_path}")
            return
        
        try:
            # Init Porcupine
            self.porcupine = pvporcupine.create(
                access_key=access_key,
                keyword_paths=[self.wake_word_path]
            )
            logger.info("✅ Porcupine initialized")
            
            # Find Jabra device
            available_devices = PvRecorder.get_available_devices()
            logger.info(f"Audio devices: {available_devices}")
            
            target_index = -1
            for i, device in enumerate(available_devices):
                if "Jabra" in device:
                    target_index = i
                    logger.info(f"✅ Jabra found at index {i}: {device}")
                    break
            
            if target_index == -1:
                logger.warning("⚠️ Jabra not found, using default (0)")
                target_index = 0
            
            self.device_index = target_index
            
            # Init Recorder
            self.recorder = PvRecorder(
                device_index=target_index,
                frame_length=self.porcupine.frame_length
            )
            
            # Test hardware
            self.recorder.start()
            self.recorder.stop()
            
            self.enabled = True
            logger.info("✅ Voice input hardware ready")
        
        except ImportError as e:
            logger.error(
                f"❌ Voice input dependencies missing: {e}\n"
                "Install with: pip install pvporcupine pvrecorder"
            )
            raise
        except (OSError, RuntimeError) as e:
            logger.error(
                f"❌ Voice input hardware setup failed: {e}",
                exc_info=True
            )
            # Cleanup su errore hardware
            if self.porcupine:
                try:
                    self.porcupine.delete()
                except Exception as cleanup_err:
                    logger.debug(f"Porcupine cleanup error: {cleanup_err}")
                self.porcupine = None
            raise RuntimeError("Voice input hardware unavailable") from e
        except Exception as e:
            logger.error(
                f"❌ Unexpected error in voice input setup: {e}",
                exc_info=True
            )
            # Cleanup
            if self.porcupine:
                try:
                    self.porcupine.delete()
                except Exception as cleanup_err:
                    logger.debug(f"Porcupine cleanup error: {cleanup_err}")
                self.porcupine = None
            raise
    
    def start(self, input_queue: PriorityQueue) -> None:
        """Avvia worker thread"""
        self.input_queue = input_queue
        self.running = True
        
        if not self.enabled:
            logger.warning("⚠️ Voice input disabled, not starting")
            return
        
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
        
        # Cleanup hardware
        if self.recorder:
            try:
                self.recorder.delete()
            except Exception as e:
                logger.debug(f"Recorder cleanup error: {e}")
        
        if self.porcupine:
            try:
                self.porcupine.delete()
            except Exception as e:
                logger.debug(f"Porcupine cleanup error: {e}")
        
        if self.led_ascolto:
            self.led_ascolto.off()
        
        logger.info(f"⏹️  {self.name} stopped")
    
    def _worker_loop(self) -> None:
        """Loop principale: Wake Word → Conversation Session"""
        logger.info("🎤 Voice input loop started (waiting for wake word)")
        
        try:
            self.recorder.start()
            
            while self.running:
                # 1. Check se device è occupato (sta parlando)
                if self.device_manager.is_speaking.is_set():
                    time.sleep(0.1)
                    continue
                
                # 2. Ascolta wake word
                pcm = self.recorder.read()
                result = self.porcupine.process(pcm)
                
                if result >= 0:
                    logger.info("✨ WAKE WORD detected!")
                    
                    # Richiedi accesso device
                    if not self.device_manager.request_input():
                        logger.warning("⚠️ Could not acquire device for input")
                        continue
                    
                    try:
                        # LED on
                        if self.led_ascolto:
                            self.led_ascolto.on()
                        
                        # Stop Porcupine recorder
                        self.recorder.stop()
                        
                        # Avvia conversation session
                        self._run_conversation_session()
                        
                        # LED off
                        if self.led_ascolto:
                            self.led_ascolto.off()
                        
                        # Resume wake word detection
                        logger.info("💤 Returning to wake word detection...")
                        self.recorder.start()
                    
                    finally:
                        # Rilascia device
                        self.device_manager.release()
        
        except Exception as e:
            logger.error(f"Voice input loop error: {e}", exc_info=True)
        
        finally:
            if self.recorder:
                try:
                    self.recorder.delete()
                except Exception as e:
                    logger.debug(f"Recorder cleanup error: {e}")
            if self.porcupine:
                try:
                    self.porcupine.delete()
                except Exception as e:
                    logger.debug(f"Porcupine cleanup error: {e}")
            if self.led_ascolto:
                self.led_ascolto.off()
    
    def _run_conversation_session(self) -> None:
        """
        Sessione conversazione continua con timeout.
        Il timeout si resetta se Buddy parla.
        """
        logger.info("🎤 Conversation session started")
        
        MAX_SILENCE_SECONDS = 15.0
        last_interaction_time = time.time()
        
        recognizer = sr.Recognizer()
        recognizer.pause_threshold = 1.0
        recognizer.non_speaking_duration = 0.5
        recognizer.dynamic_energy_threshold = False
        recognizer.energy_threshold = 400
        
        try:
            with SuppressStream():
                mic_source = sr.Microphone(device_index=self.device_index)
            
            with mic_source as source:
                while self.running:
                    # 1. Check se Buddy sta parlando
                    if self.device_manager.is_speaking.is_set():
                        # Reset timeout mentre parla
                        last_interaction_time = time.time()
                        time.sleep(0.1)
                        continue
                    
                    # 2. Check timeout
                    elapsed = time.time() - last_interaction_time
                    if elapsed > MAX_SILENCE_SECONDS:
                        logger.info(f"⏳ Silence timeout ({MAX_SILENCE_SECONDS}s), ending session")
                        break
                    
                    try:
                        # 3. Ascolta (con timeout breve per polling)
                        audio = recognizer.listen(source, timeout=1.0, phrase_time_limit=15)
                        
                        # Reset timeout
                        last_interaction_time = time.time()
                        
                        # Processa audio
                        self._process_audio(recognizer, audio)
                    
                    except sr.WaitTimeoutError:
                        # Nessun audio, continua loop
                        pass
                    except Exception as e:
                        logger.warning(f"Error in conversation session: {e}")
        
        except Exception as e:
            logger.error(f"Error opening microphone: {e}")
        
        logger.info("🎤 Conversation session ended")
    
    def _process_audio(self, recognizer: sr.Recognizer, audio) -> None:
        """Processa audio e crea evento"""
        try:
            text = recognizer.recognize_google(audio, language="it-IT")
            
            if text:
                logger.info(f"🗣️  Recognized: {text}")
                
                # Crea evento
                event = create_input_event(
                    EventType.USER_SPEECH,
                    text,
                    source="voice",
                    priority=EventPriority.HIGH
                )
                
                self.input_queue.put(event)
        
        except sr.UnknownValueError:
            # Suono non riconosciuto, ignora
            pass
        except Exception as e:
            logger.error(f"Speech recognition error: {e}")


class MockVoiceInput(VoiceInputPort):
    """
    Mock Voice Input per testing.
    Genera frasi simulate per testare il sistema.
    """
    
    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        
        self.interval = config.get('interval', 10.0)
        self.worker_thread = None
        
        # Frasi di test simulate
        self.test_phrases = [
            "Ciao, come stai?",
            "Che ore sono?",
            "Raccontami una barzelletta",
            "Qual è la temperatura?",
            "Test del sistema vocale"
        ]
        
        logger.info(f"🎤 MockVoiceInput initialized")
    
    def start(self, input_queue: PriorityQueue) -> None:
        """Avvia worker"""
        self.input_queue = input_queue
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
        """Loop che genera frasi simulate"""
        counter = 0
        
        while self.running:
            try:
                # Cicla tra le frasi di test
                phrase = self.test_phrases[counter % len(self.test_phrases)]
                
                logger.info(f"🎤 [MOCK] Voice input: {phrase}")
                
                # Crea evento
                event = create_input_event(
                    EventType.USER_SPEECH,
                    phrase,
                    source="voice_mock",
                    priority=EventPriority.HIGH
                )
                
                self.input_queue.put(event)
                counter += 1
            
            except Exception as e:
                logger.error(f"Mock voice input error: {e}")
            
            time.sleep(self.interval)
