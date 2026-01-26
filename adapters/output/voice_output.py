"""
Voice Output Adapters - TTS e Speech Output
"""

import os
import time
import logging
import threading
import subprocess
from queue import PriorityQueue, Empty
from typing import Optional

from gtts import gTTS
from google.cloud import texttospeech

from adapters.ports import OutputPort
from adapters.shared_audio_state import is_speaking, find_jabra_alsa
from core.events import OutputEvent, OutputEventType, EventPriority
from core.commands import AdapterCommand

logger = logging.getLogger(__name__)


class JabraVoiceOutput(OutputPort):
    """
    Voice Output con Jabra - Implementazione REALE.
    Gestisce TTS (gTTS o Piper) e LED di stato.
    Usa AudioDeviceManager per coordinamento con input.
    """
    
    def __init__(self, name: str, config: dict):
        queue_maxsize = config.get('queue_maxsize', 50)
        super().__init__(name, config, queue_maxsize)
        
        # Configurazione TTS
        self.tts_mode = config['tts_mode']  # 'cloud', 'local' o 'texttospeech'
        self.voice_name = config['voice_name']
        
        # Auto-detect Jabra device (ALSA)
        audio_device = find_jabra_alsa()
        if not audio_device:
            raise RuntimeError("Jabra audio device not found for output")
        self.audio_device: str = audio_device  # Guaranteed non-None after check
        logger.info(f"✅ Jabra output auto-detected: {self.audio_device}")
        
        
        # Setup Piper (se local mode)
        if self.tts_mode == "local":
            self._setup_piper()
        
        if self.tts_mode == "texttospeech":
            self._setup_texttospeech()

        # Thread worker
        self.worker_thread: Optional[threading.Thread] = None
        self._playback_process: Optional[subprocess.Popen] = None
        
        logger.info(f"🔊 JabraVoiceOutput initialized (mode: {self.tts_mode}, voice: {self.voice_name}, device: {self.audio_device})")
    
    @classmethod
    def handled_events(cls):
        """Eventi gestiti da questo adapter"""
        return [OutputEventType.SPEAK]

    def supported_commands(self):
        """Dichiara comandi supportati"""
        return {AdapterCommand.VOICE_OUTPUT_STOP}

    def handle_command(self, command: AdapterCommand) -> bool:
        """Gestisce comandi"""
        if command == AdapterCommand.VOICE_OUTPUT_STOP:
            if self._playback_process and self._playback_process.poll() is None:
                logger.info("🛑 Stopping voice output")
                self._playback_process.terminate()
                self._playback_process = None
                is_speaking.clear()
                return True
        return False
    
    def _setup_piper(self):
        """Setup Piper TTS locale
        
        Raises:
            ValueError: If voice not supported
            FileNotFoundError: If piper binary or model not found
        """
        home = os.path.expanduser("~")
        self.piper_base_path = os.path.join(home, "buddy_tools/piper")
        self.piper_binary = os.path.join(self.piper_base_path, "piper/piper")
        
        # Fail fast: binary deve esistere
        if not os.path.isfile(self.piper_binary):
            raise FileNotFoundError(
                f"Piper binary not found: {self.piper_binary}. "
                f"Install with: bash scripts/install_piper.sh"
            )
        
        voice_map = {
            "paola": {"file": "it_IT-paola-medium.onnx", "speed": "1.0"},
            "riccardo": {"file": "it_IT-riccardo-x_low.onnx", "speed": "1.1"}
        }
        
        # Fail fast: voice deve essere supportata
        if self.voice_name not in voice_map:
            raise ValueError(
                f"Voice '{self.voice_name}' not supported. "
                f"Available: {list(voice_map.keys())}"
            )
        
        selected_config = voice_map[self.voice_name]
        self.piper_model = os.path.join(self.piper_base_path, selected_config["file"])
        self.piper_speed = selected_config["speed"]
        
        # Fail fast: model deve esistere
        if not os.path.isfile(self.piper_model):
            raise FileNotFoundError(
                f"Piper model not found: {self.piper_model}. "
                f"Download models from Piper releases."
            )

    def _setup_texttospeech(self):
        """Setup Google Cloud Text-to-Speech
        
        Raises:
            ValueError: If voice not supported
        """
        # For now, no specific setup is needed, but we can check credentials here
        if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable is not set.")
        logger.info("✅ Google Cloud Text-to-Speech configured.")
    
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
        """Gestisce evento SPEAK"""
        text = str(event.content)
        
        # Sanifica testo
        text = text.replace('"', '').replace("'", "")
        
        logger.info(f"🗣️  Speaking: {text[:50]}...")
        
        try:
            is_speaking.set()
            
            # TTS
            if self.tts_mode == "local":
                self._speak_piper(text)
            elif self.tts_mode == "texttospeech":
                self._speak_texttospeech(text)
            else:
                self._speak_gtts(text)
        
        except Exception as e:
            logger.error(f"TTS error: {e}")
        
        finally:
            is_speaking.clear()
    
    def _speak_gtts(self, text: str) -> None:
        """TTS usando Google gTTS (cloud)
        
        Raises:
            Exception: Se sintesi o playback falliscono
        """
        filename: Optional[str] = None
        try:
            # Genera TTS
            logger.debug(f"Generating gTTS for: {text[:50]}...")
            tts = gTTS(text=text, lang='it')
            filename = f"/tmp/buddy_tts_{time.time()}.mp3"
            tts.save(filename)
            logger.debug(f"TTS saved to {filename}")
            
            # Fail-fast: filename must be set here
            assert filename is not None, "TTS file generation failed"
            
            # Play audio con mpg123 su device configurato
            logger.debug(f"Playing with mpg123 on device {self.audio_device}...")
            self._playback_process = subprocess.Popen(
                ["mpg123", "-a", self.audio_device, "-q", filename],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            self._playback_process.wait()
            logger.debug(f"mpg123 completed successfully")
        
        except FileNotFoundError as e:
            logger.error(f"❌ mpg123 not found - install with: sudo apt-get install mpg123")
            raise
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ mpg123 failed: {e.stderr.decode() if e.stderr else 'unknown error'}")
            raise
        except Exception as e:
            logger.error(f"❌ gTTS error: {e}", exc_info=True)
            raise
        finally:
            # Cleanup sempre
            if filename and os.path.exists(filename):
                try:
                    os.remove(filename)
                    logger.debug(f"Cleaned up {filename}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup {filename}: {e}")
    
    def _speak_piper(self, text: str) -> None:
        """TTS usando Piper (local)
        
        Raises:
            Exception: Se pipeline fallisce
        """
        try:
            piper_cmd = [
                self.piper_binary,
                "--model", self.piper_model,
                "--length_scale", self.piper_speed,
                "--output_file", "-"
            ]
            sox_cmd = ["sox", "-t", "wav", "-", "-r", "48000", "-t", "wav", "-"]
            aplay_cmd = ["aplay", "-D", self.audio_device]
            
            # Pipeline: Piper -> Sox -> Aplay
            p_piper = subprocess.Popen(
                piper_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            p_sox = subprocess.Popen(
                sox_cmd,
                stdin=p_piper.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self._playback_process = subprocess.Popen(
                aplay_cmd,
                stdin=p_sox.stdout,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            p_aplay = self._playback_process
            
            # Close stdout per consentire pipe chain di chiudersi correttamente
            if p_piper.stdout:
                p_piper.stdout.close()
            if p_sox.stdout:
                p_sox.stdout.close()
            
            # Comunica input a piper
            stdout_data, stderr_data = p_piper.communicate(input=text.encode('utf-8'))
            p_aplay.wait()
            
            if p_piper.returncode != 0:
                error_msg = stderr_data.decode() if stderr_data else "Unknown error"
                logger.error(f"Piper error: {error_msg}")
                raise RuntimeError(f"Piper failed with return code {p_piper.returncode}")
        
        except Exception as e:
            logger.error(f"Piper TTS error: {e}")
            raise

    def _speak_texttospeech(self, text: str) -> None:
        """TTS using Google Cloud Text-to-Speech (cloud)
        
        Raises:
            Exception: If synthesis or playback fail
        """
        filename: Optional[str] = None
        try:
            # Check if credentials are set
            if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
                logger.error("Error: GOOGLE_APPLICATION_CREDENTIALS environment variable is not set.")
                return

            client = texttospeech.TextToSpeechClient()

            input_text = texttospeech.SynthesisInput(text=text)

            voice = texttospeech.VoiceSelectionParams(
                language_code="it-IT",
                name=self.voice_name,
            )

            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )

            response = client.synthesize_speech(
                request={"input": input_text, "voice": voice, "audio_config": audio_config}
            )

            filename = f"/tmp/buddy_tts_{time.time()}.mp3"
            with open(filename, "wb") as out:
                out.write(response.audio_content)
            logger.debug(f"TTS saved to {filename}")

            # Fail-fast: filename must be set here
            assert filename is not None, "TTS file generation failed"
            
            # Play audio con mpg123 su device configurato
            logger.debug(f"Playing with mpg123 on device {self.audio_device}...")
            self._playback_process = subprocess.Popen(
                ["mpg123", "-a", self.audio_device, "-q", filename],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            self._playback_process.wait()
            logger.debug(f"mpg123 completed successfully")
        
        except FileNotFoundError as e:
            logger.error(f"❌ mpg123 not found - install with: sudo apt-get install mpg123")
            raise
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ mpg123 failed: {e.stderr.decode() if e.stderr else 'unknown error'}")
            raise
        except Exception as e:
            logger.error(f"❌ TextToSpeech error: {e}", exc_info=True)
            raise
        finally:
            # Cleanup sempre
            if filename and os.path.exists(filename):
                try:
                    os.remove(filename)
                    logger.debug(f"Cleaned up {filename}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup {filename}: {e}")

