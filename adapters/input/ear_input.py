"""
Ear Input Adapter - Speech Recognition dedicato
Gestisce solo il riconoscimento vocale, non la wake word detection.
"""

import os
import time
import logging
import threading
from queue import PriorityQueue
from typing import Optional

import speech_recognition as sr

from adapters.ports import InputPort
from adapters.audio_device_manager import get_jabra_manager
from core.events import create_input_event, create_output_event, InputEventType, OutputEventType, EventPriority
from core.commands import AdapterCommand

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


class EarInput(InputPort):
    """
    Ear Input - Speech Recognition senza Wake Word.
    
    - NON parte automaticamente
    - Parte solo su comando VOICE_INPUT_START
    - Gestisce sessioni conversazionali con timeout
    - Rilascia device quando la conversazione termina
    - Coordina con AudioDeviceManager per evitare conflitti
    """
    
    def __init__(self, config: dict, input_queue: PriorityQueue):
        super().__init__(name="ear_input", config=config, input_queue=input_queue)
        
        # Configurazione
        self.stt_mode = config['stt_mode']
        self.max_silence_seconds = config['max_silence_seconds']
        
        # Auto-detect Jabra device
        from adapters.audio_device_manager import find_jabra_pyaudio
        self.device_index = find_jabra_pyaudio()
        if self.device_index is None:
            raise RuntimeError("Jabra device not found for EarInput")
        logger.info(f"✅ Jabra auto-detected for EarInput: PyAudio index={self.device_index}")
        
        # Device Manager per coordinamento
        self.device_manager = get_jabra_manager()
        
        # Stato conversazione
        self._conversation_active = False
        self._conversation_thread: Optional[threading.Thread] = None
        self._stop_conversation = threading.Event()
        
        # Riconoscitore configurato
        self._recognizer = self._setup_recognizer()
        
        logger.info(f"👂 EarInput initialized (device_index={self.device_index})")
    
    def _setup_recognizer(self) -> sr.Recognizer:
        """Configura speech recognizer con parametri ottimizzati"""
        recognizer = sr.Recognizer()
        recognizer.pause_threshold = 1.0
        recognizer.non_speaking_duration = 0.5
        recognizer.dynamic_energy_threshold = False
        recognizer.energy_threshold = 400
        return recognizer
    
    def start(self) -> None:
        """
        Start adapter (ma NON inizia ascolto).
        L'ascolto parte solo su comando VOICE_INPUT_START.
        """
        self.running = True
        logger.info(f"▶️  {self.name} started (waiting for VOICE_INPUT_START command)")
    
    def stop(self) -> None:
        """Ferma adapter e eventuali conversazioni attive"""
        logger.info(f"⏸️  Stopping {self.name}...")
        self.running = False
        
        # Ferma conversazione se attiva
        if self._conversation_active:
            self._stop_conversation.set()
            if self._conversation_thread and self._conversation_thread.is_alive():
                self._conversation_thread.join(timeout=3.0)
        
        logger.info(f"⏹️  {self.name} stopped")
    
    def supported_commands(self):
        """Dichiara comandi supportati"""
        return {
            AdapterCommand.VOICE_INPUT_START,
            AdapterCommand.VOICE_INPUT_STOP
        }
    
    def handle_command(self, command: AdapterCommand) -> bool:
        """
        Gestisce comandi di controllo dal Brain.
        
        Args:
            command: Comando da eseguire
            
        Returns:
            True se gestito, False se ignorato
        """
        if command == AdapterCommand.VOICE_INPUT_START:
            if not self._conversation_active:
                self._start_conversation()
                return True
            else:
                logger.debug("Conversation already active, ignoring START")
                return True
        
        elif command == AdapterCommand.VOICE_INPUT_STOP:
            if self._conversation_active:
                self._stop_conversation.set()
                return True
            else:
                logger.debug("No conversation active, ignoring STOP")
                return True
        
        return False
    
    def _start_conversation(self) -> None:
        """Avvia thread conversazione"""
        if self._conversation_active:
            logger.warning("⚠️  Conversation already active")
            return
        
        self._conversation_active = True
        self._stop_conversation.clear()
        
        self._conversation_thread = threading.Thread(
            target=self._conversation_loop,
            daemon=True,
            name=f"{self.name}_conversation"
        )
        self._conversation_thread.start()
        
        logger.info("🎤 Conversation thread started")
    
    def _conversation_loop(self) -> None:
        """
        Loop conversazione continua con timeout.
        Il timeout si resetta se Buddy parla.
        """
        logger.info("👂 Ear conversation session started")
        
        # Richiedi accesso device
        if not self.device_manager.request_input():
            logger.warning("⚠️  Could not acquire device for input")
            self._conversation_active = False
            return
        
        last_interaction_time = time.time()
        
        try:
            # Apri microfono
            with SuppressStream():
                mic_source = sr.Microphone(device_index=self.device_index)
            
            with mic_source as source:
                while self.running and not self._stop_conversation.is_set():
                    # 1. Check se Buddy sta parlando
                    if self.device_manager.is_speaking.is_set():
                        # Reset timeout mentre parla
                        last_interaction_time = time.time()
                        time.sleep(0.1)
                        continue
                    
                    # 2. Check timeout
                    elapsed = time.time() - last_interaction_time
                    if elapsed > self.max_silence_seconds:
                        logger.info(f"⏳ Silence timeout ({self.max_silence_seconds}s), ending session")
                        break
                    
                    try:
                        # 3. Ascolta (con timeout breve per polling)
                        audio = self._recognizer.listen(source, timeout=1.0, phrase_time_limit=15)
                        
                        # Reset timeout
                        last_interaction_time = time.time()
                        
                        # Processa audio
                        self._process_audio(audio)
                    
                    except sr.WaitTimeoutError:
                        # Nessun audio, continua loop
                        pass
                    except Exception as e:
                        logger.error(f"Error in conversation loop: {e}")
                        break
        
        except Exception as e:
            logger.error(f"Error opening microphone: {e}", exc_info=True)
        
        finally:
            # Rilascia device
            self.device_manager.release()
            
            self._conversation_active = False
            logger.info("👂 Ear conversation session ended")
    
    def _process_audio(self, audio) -> None:
        """Processa audio e crea evento USER_SPEECH"""
        try:
            text = self._recognizer.recognize_google(audio, language="it-IT")  # type: ignore[attr-defined]
            
            if text:
                logger.info(f"🗣️  Recognized: {text}")
                
                # Crea evento
                event = create_input_event(
                    InputEventType.USER_SPEECH,
                    text,
                    source="ear",
                    priority=EventPriority.HIGH
                )
                
                self.input_queue.put(event)
        
        except sr.UnknownValueError:
            # Suono non riconosciuto, ignora
            logger.debug("Audio not recognized, ignoring")
        except Exception as e:
            logger.error(f"Speech recognition error: {e}", exc_info=True)


class MockEarInput(InputPort):
    """
    Mock Ear Input per testing.
    Simula riconoscimento vocale senza hardware.
    """
    
    def __init__(self, config: dict, input_queue: PriorityQueue):
        super().__init__(name="mock_ear_input", config=config, input_queue=input_queue)
        
        self._conversation_active = False
        self._conversation_thread: Optional[threading.Thread] = None
        self._stop_conversation = threading.Event()
        
        # Frasi simulate
        self.test_phrases = [
            "Ciao, come stai?",
            "Che ore sono?",
            "Raccontami una barzelletta",
            "Grazie, è tutto",
        ]
        self.phrase_index = 0
        
        logger.info(f"👂 MockEarInput initialized")
    
    def start(self) -> None:
        """Start adapter"""
        self.running = True
        logger.info(f"▶️  {self.name} started (waiting for VOICE_INPUT_START)")
    
    def stop(self) -> None:
        """Stop adapter"""
        self.running = False
        if self._conversation_active:
            self._stop_conversation.set()
            if self._conversation_thread:
                self._conversation_thread.join(timeout=2.0)
        logger.info(f"⏹️  {self.name} stopped")
    
    def supported_commands(self):
        """Dichiara comandi supportati"""
        return {
            AdapterCommand.VOICE_INPUT_START,
            AdapterCommand.VOICE_INPUT_STOP
        }
    
    def handle_command(self, command: AdapterCommand) -> bool:
        """Gestisce comandi"""
        if command == AdapterCommand.VOICE_INPUT_START:
            if not self._conversation_active:
                self._start_conversation()
            return True
        
        elif command == AdapterCommand.VOICE_INPUT_STOP:
            if self._conversation_active:
                self._stop_conversation.set()
            return True
        
        return False
    
    def _start_conversation(self) -> None:
        """Avvia mock conversation"""
        if self._conversation_active:
            return
        
        self._conversation_active = True
        self._stop_conversation.clear()
        
        self._conversation_thread = threading.Thread(
            target=self._mock_conversation_loop,
            daemon=True,
            name=f"{self.name}_conversation"
        )
        self._conversation_thread.start()
        
        logger.info("🎤 [MOCK] Conversation started")
    
    def _mock_conversation_loop(self) -> None:
        """Simula conversazione con 3 frasi e poi termina"""
        try:
            phrases_count = 0
            max_phrases = 3
            
            while self.running and not self._stop_conversation.is_set() and phrases_count < max_phrases:
                # Simula tempo di ascolto
                time.sleep(2.0)
                
                if self._stop_conversation.is_set():
                    break
                
                # Genera frase
                phrase = self.test_phrases[self.phrase_index % len(self.test_phrases)]
                self.phrase_index += 1
                phrases_count += 1
                
                logger.info(f"👂 [MOCK] Recognized: {phrase}")
                
                # Emetti evento
                event = create_input_event(
                    InputEventType.USER_SPEECH,
                    phrase,
                    source="ear_mock",
                    priority=EventPriority.HIGH
                )
                self.input_queue.put(event)
                
                # Simula tempo di processing
                time.sleep(1.0)
            
            logger.info(f"👂 [MOCK] Conversation ended after {phrases_count} phrases")
        
        except Exception as e:
            logger.error(f"Mock conversation error: {e}")
        
        finally:
            self._conversation_active = False
