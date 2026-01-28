"""
Voice Output Adapters - TTS e Speech Output
"""

import os
import logging
import threading
import subprocess
from queue import Empty
from typing import Optional

from adapters.ports import OutputPort
from adapters.audio_utils import find_jabra_alsa
from adapters.tts_engines import TTSEngine, create_tts_engine
from core.state import global_state
from core.events import OutputEvent, OutputEventType
from core.commands import AdapterCommand

logger = logging.getLogger(__name__)


class JabraVoiceOutput(OutputPort):
    """
    Voice Output con Jabra - Implementazione REALE.
    Gestisce TTS tramite motori pluggabili e playback audio.
    
    Responsabilità:
    - TTS Engine: sintetizza text → file audio
    - Voice Adapter: gestisce playback, lifecycle, stop/pause
    """
    
    def __init__(self, name: str, config: dict):
        queue_maxsize = config.get('queue_maxsize', 50)
        super().__init__(name, config, queue_maxsize)
        
        # Configurazione TTS
        tts_mode = config['tts_mode']  # 'cloud', 'local' o 'texttospeech'
        voice_name = config['voice_name']
        
        # Auto-detect Jabra device (ALSA)
        audio_device = find_jabra_alsa()
        if not audio_device:
            raise RuntimeError("Jabra audio device not found for output")
        self.audio_device: str = audio_device
        logger.info(f"✅ Jabra output auto-detected: {self.audio_device}")
        
        # Crea motore TTS (fail-fast se config invalida)
        self.tts_engine: TTSEngine = create_tts_engine(tts_mode, voice_name)
        
        # Playback management
        self.worker_thread: Optional[threading.Thread] = None
        self._playback_process: Optional[subprocess.Popen] = None
        
        logger.info(f"🔊 JabraVoiceOutput initialized (mode: {tts_mode}, voice: {voice_name})")
    
    @classmethod
    def handled_events(cls):
        """Eventi gestiti da questo adapter"""
        return [OutputEventType.SPEAK]

    def supported_commands(self):
        """Dichiara comandi supportati"""
        return {AdapterCommand.VOICE_OUTPUT_STOP}

    def handle_command(self, command: AdapterCommand) -> bool:
        """Gestisce comandi di controllo playback"""
        if command == AdapterCommand.VOICE_OUTPUT_STOP:
            if self._playback_process and self._playback_process.poll() is None:
                logger.info("🛑 Stopping voice output")
                self._playback_process.terminate()
                self._playback_process = None
                global_state.is_speaking.clear()
                return True
            else:
                logger.info("No active voice output to stop")
        return False
    
    def start(self) -> None:
        """Avvia il worker thread che consuma dalla coda interna"""
        self.running = True
        
        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name=f"{self.name}_worker"
        )
        self.worker_thread.start()
        
        logger.info(f"▶️  {self.name} started")
    
    def stop(self) -> None:
        """Ferma il worker thread"""
        logger.info(f"⏸️  Stopping {self.name}...")
        self.running = False
        
        # Aspetta thread con timeout
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=3.0)
            if self.worker_thread.is_alive():
                logger.warning(f"⚠️  {self.name} thread did not terminate")
         
        logger.info(f"⏹️  {self.name} stopped")
    
    def _worker_loop(self) -> None:
        """Loop principale che processa eventi dalla queue"""
        while self.running:
            try:
                # Preleva evento con timeout
                event = self.output_queue.get(timeout=0.5)
                
                if event.type == OutputEventType.SPEAK:
                    self._handle_speak_event(event)
                
                self.output_queue.task_done()
                
            except Empty:
                continue
            except KeyboardInterrupt:
                logger.info("Voice output worker interrupted")
                break
            except Exception as e:
                logger.error(
                    f"Error in voice output worker: {e}",
                    exc_info=True  # Full stack trace per debugging
                )
                # Continue loop - un errore non deve fermare il worker
    
    def _handle_speak_event(self, event: OutputEvent) -> None:
        """Gestisce evento SPEAK: sintesi + playback + cleanup"""
        text = str(event.content)
        
        # Sanifica testo
        text = text.replace('"', '').replace("'", "")
        
        logger.info(f"🗣️  Speaking: {text[:50]}...")
        
        audio_file: Optional[str] = None
        try:
            global_state.is_speaking.set()
            
            # 1. Sintesi TTS (text → file)
            audio_file = self.tts_engine.synthesize(text)
            
            # 2. Playback (file → audio device)
            self._play_audio_file(audio_file)
        
        except Exception as e:
            logger.error(f"TTS/Playback error: {e}")
        
        finally:
            # 3. Cleanup file temporaneo
            if audio_file and os.path.exists(audio_file):
                try:
                    os.remove(audio_file)
                    logger.debug(f"Cleaned up {audio_file}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup {audio_file}: {e}")
            
            global_state.is_speaking.clear()
    
    def _play_audio_file(self, filename: str) -> None:
        """Riproduce file audio su device Jabra
        
        Args:
            filename: Path del file audio da riprodurre
        
        Raises:
            FileNotFoundError: Se mpg123/aplay non installato
            RuntimeError: Se playback fallisce
        """
        # Determina player in base al formato
        if filename.endswith('.wav'):
            # Usa aplay per WAV (Piper)
            logger.debug(f"Playing WAV with aplay on device {self.audio_device}...")
            self._playback_process = subprocess.Popen(
                ["aplay", "-D", self.audio_device, filename],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        else:
            # Usa mpg123 per MP3 (gTTS, Cloud TTS)
            logger.debug(f"Playing MP3 with mpg123 on device {self.audio_device}...")
            self._playback_process = subprocess.Popen(
                ["mpg123", "-a", self.audio_device, "-q", filename],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        
        # Aspetta completamento
        self._playback_process.wait()
        
        if self._playback_process.returncode != 0:
            stderr = self._playback_process.stderr.read().decode() if self._playback_process.stderr else "unknown error"
            raise RuntimeError(f"Playback failed: {stderr}")
        
        logger.debug("Playback completed successfully")

