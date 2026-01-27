"""
Ear Input Adapter - Speech Recognition dedicato
Gestisce solo il riconoscimento vocale, non la wake word detection.
"""

import os
import time
import logging
import threading
from queue import PriorityQueue, Queue
from typing import Optional

import speech_recognition as sr

from adapters.ports import InputPort
from adapters.audio_utils import find_jabra_pyaudio, SuppressStream
from core.state import global_state
from core.events import create_input_event, create_output_event, InputEventType, OutputEventType, EventPriority
from core.commands import AdapterCommand

logger = logging.getLogger(__name__)


class EarInput(InputPort):
    """
    Ear Input - Speech Recognition senza Wake Word.
    
    - NON parte automaticamente
    - Parte solo su comando VOICE_INPUT_START
    - Gestisce sessioni conversazionali con timeout
    - Rilascia device quando la conversazione termina
    - Coordina con AudioDeviceManager per evitare conflitti
    """
    
    def __init__(self, name: str, config: dict, input_queue: PriorityQueue):
        super().__init__(name, config, input_queue)
        
        # Configurazione
        self.stt_mode = config['stt_mode']
        self.max_silence_seconds = config['max_silence_seconds']
        
        # Auto-detect Jabra device
        self.device_index = find_jabra_pyaudio()
        if self.device_index is None:
            raise RuntimeError("Jabra device not found for EarInput")
        logger.info(f"✅ Jabra auto-detected for EarInput: PyAudio index={self.device_index}")
        
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
        
        # Piccolo delay per dare tempo al wakeword di rilasciare il dispositivo
        time.sleep(0.2)
        
        last_interaction_time = time.time()
        mic_source = None
        
        try:
            # Apri microfono con retry
            with SuppressStream():
                try:
                    mic_source = sr.Microphone(device_index=self.device_index)
                except Exception as e:
                    logger.error(f"Failed to create Microphone object: {e}")
                    raise
            
            # Verifica che il microfono sia stato creato correttamente
            if mic_source is None:
                raise RuntimeError("Microphone object is None")
            
            # Prova ad aprire il microfono (context manager)
            try:
                mic_source.__enter__()
            except Exception as e:
                logger.error(f"Failed to open microphone stream: {e}")
                raise
            
            try:
                source = mic_source
                buddy_was_speaking = False
                while self.running and not self._stop_conversation.is_set():
                    # Se Buddy ha appena smesso di parlare, resetta il timer
                    if buddy_was_speaking and not global_state.is_speaking.is_set():
                        logger.debug("Buddy finished speaking, resetting silence timer.")
                        last_interaction_time = time.time()

                    # Aggiorna lo stato di "is_speaking" per il prossimo ciclo
                    buddy_was_speaking = global_state.is_speaking.is_set()
                    
                    # 1. Check timeout se NON sta parlando
                    if not global_state.is_speaking.is_set():
                        elapsed = time.time() - last_interaction_time
                        if elapsed > self.max_silence_seconds:
                            logger.info(f"⏳ Silence timeout ({self.max_silence_seconds}s), ending session")
                            break
                    
                    try:
                        # 2. Ascolta (con timeout breve per polling)
                        audio = self._recognizer.listen(source, timeout=1.0, phrase_time_limit=15)
                        
                        # 3. Se sente qualcosa, resetta il timeout
                        last_interaction_time = time.time()
                        
                        # 4. Processa audio. Se sta parlando, è un'interruzione
                        is_barge_in = global_state.is_speaking.is_set()
                        self._process_audio(audio, False)
                    
                    except sr.WaitTimeoutError:
                        # Nessun audio, continua loop
                        pass
                    except Exception as e:
                        logger.error(f"Error in conversation loop: {e}")
                        break
            finally:
                # Chiudi il context manager del microfono
                if mic_source is not None:
                    try:
                        mic_source.__exit__(None, None, None)
                    except Exception as e:
                        logger.error(f"Error closing microphone: {e}")
        
        except Exception as e:
            logger.error(f"Error in microphone setup: {e}", exc_info=True)
        
        finally:
            # Invia evento CONVERSATION_END che il Brain gestirà
            # (spegnerà LED e riattiva wakeword)
            conversation_end_event = create_input_event(
                InputEventType.CONVERSATION_END,
                None,
                source="ear_input",
                priority=EventPriority.HIGH
            )
            self.input_queue.put(conversation_end_event)
            
            self._conversation_active = False
            logger.info("👂 Ear conversation session ended")
    
    def _process_audio(self, audio, is_barge_in: bool = False) -> None:
        """Processa audio e crea evento.
        
        Args:
            audio: Dati audio da processare
            is_barge_in: Se True, invia un evento INTERRUPT
        """
        try:
            text = self._recognizer.recognize_google(audio, language="it-IT")  # type: ignore[attr-defined]
            
            if not text:
                return

            logger.info(f"🗣️  Recognized: {text}")
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
