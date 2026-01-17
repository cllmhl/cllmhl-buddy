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

# Mock GPIO per testing
if not os.path.exists('/proc/device-tree/model'):
    os.environ['GPIOZERO_PIN_FACTORY'] = 'mock'

from gpiozero import LED

from adapters.ports import VoiceOutputPort
from adapters.audio_device_manager import get_jabra_manager
from core.events import Event, OutputEventType

logger = logging.getLogger(__name__)


class JabraVoiceOutput(VoiceOutputPort):
    """
    Voice Output con Jabra - Implementazione REALE.
    Gestisce TTS (gTTS o Piper) e LED di stato.
    Usa AudioDeviceManager per coordinamento con input.
    """
    
    def __init__(self, name: str, config: dict):
        queue_maxsize = config.get('queue_maxsize', 50)
        super().__init__(name, config, queue_maxsize)
        
        # Configurazione TTS
        self.tts_mode = config.get('tts_mode', 'cloud').lower()  # 'cloud' o 'local'
        self.voice_name = config.get('voice_name', 'paola').lower()
        
        # LED di stato (GPIO 21)
        self.led_pin = config.get('led_stato_pin', 21)
        # LED di stato è OPZIONALE (solo per visual feedback)
        self.led_stato = None
        try:
            self.led_stato = LED(self.led_pin)
            logger.info(f"✅ LED status on GPIO {self.led_pin}")
        except Exception as e:
            logger.warning(f"⚠️  LED status initialization failed: {e}")
            logger.warning("Continuing without LED status indicator (non-critical)")
        
        # Device Manager per coordinamento Jabra
        self.device_manager = get_jabra_manager()
        
        # Setup Piper (se local mode)
        if self.tts_mode == 'local':
            self._setup_piper()
        
        # Thread worker
        self.worker_thread = None
        
        logger.info(f"🔊 JabraVoiceOutput initialized (mode: {self.tts_mode}, voice: {self.voice_name})")
    
    def _setup_piper(self):
        """Setup Piper TTS locale"""
        home = os.path.expanduser("~")
        self.piper_base_path = os.path.join(home, "buddy_tools/piper")
        self.piper_binary = os.path.join(self.piper_base_path, "piper/piper")
        
        voice_map = {
            "paola": {"file": "it_IT-paola-medium.onnx", "speed": "1.0"},
            "riccardo": {"file": "it_IT-riccardo-x_low.onnx", "speed": "1.1"}
        }
        
        if self.voice_name not in voice_map:
            logger.warning(f"Voice '{self.voice_name}' not found, using paola")
            self.voice_name = "paola"
        
        selected_config = voice_map[self.voice_name]
        self.piper_model = os.path.join(self.piper_base_path, selected_config["file"])
        self.piper_speed = selected_config["speed"]
    
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
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=2.0)
        
        if self.led_stato:
            self.led_stato.off()
        
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
    
    def _handle_speak_event(self, event: Event) -> None:
        """Gestisce evento SPEAK"""
        text = str(event.content)
        
        # Sanifica testo
        text = text.replace('"', '').replace("'", "")
        
        logger.info(f"🗣️  Speaking: {text[:50]}...")
        
        try:
            # Richiedi accesso al device (blocca input)
            if not self.device_manager.request_output():
                logger.warning("⚠️ Could not acquire audio device for output")
                return
            
            # LED on
            if self.led_stato:
                self.led_stato.on()
            
            # TTS
            if self.tts_mode == "local":
                self._speak_piper(text)
            else:
                self._speak_gtts(text)
        
        except Exception as e:
            logger.error(f"TTS error: {e}")
        
        finally:
            # LED off
            if self.led_stato:
                self.led_stato.off()
            
            # Rilascia device (sblocca input)
            self.device_manager.release()
    
    def _speak_gtts(self, text: str) -> None:
        """TTS usando Google gTTS (cloud)"""
        try:
            tts = gTTS(text=text, lang='it')
            filename = f"/tmp/buddy_tts_{time.time()}.mp3"
            tts.save(filename)
            
            # Play audio
            subprocess.run(
                ["mpg123", "-q", filename],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                check=False
            )
            
            # Cleanup
            if os.path.exists(filename):
                os.remove(filename)
        
        except Exception as e:
            logger.error(f"gTTS error: {e}")
    
    def _speak_piper(self, text: str) -> None:
        """TTS usando Piper (local)"""
        try:
            piper_cmd = [
                self.piper_binary,
                "--model", self.piper_model,
                "--length_scale", self.piper_speed,
                "--output_file", "-"
            ]
            sox_cmd = ["sox", "-t", "wav", "-", "-r", "48000", "-t", "wav", "-"]
            aplay_cmd = ["aplay", "-D", "plughw:0,0"]
            
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
            p_aplay = subprocess.Popen(
                aplay_cmd,
                stdin=p_sox.stdout,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            p_piper.stdout.close()
            p_sox.stdout.close()
            
            _, stderr = p_piper.communicate(input=text.encode('utf-8'))
            p_aplay.wait()
            
            if p_piper.returncode != 0:
                logger.error(f"Piper error: {stderr.decode()}")
        
        except Exception as e:
            logger.error(f"Piper TTS error: {e}")


class MockVoiceOutput(VoiceOutputPort):
    """
    Mock Voice Output per testing.
    Scrive nel log applicativo invece di parlare.
    """
    
    def __init__(self, name: str, config: dict):
        queue_maxsize = config.get('queue_maxsize', 50)
        super().__init__(name, config, queue_maxsize)
        self.worker_thread = None
        logger.info(f"🔊 MockVoiceOutput initialized")
    
    def start(self) -> None:
        """Avvia worker che consuma dalla coda interna"""
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
        """Loop worker"""
        while self.running:
            try:
                event = self.output_queue.get(timeout=0.5)
                
                if event.type == OutputEventType.SPEAK:
                    self._handle_speak_event(event)
                
                self.output_queue.task_done()
                
            except Empty:
                continue
            except KeyboardInterrupt:
                logger.info("Mock voice worker interrupted")
                break
            except Exception as e:
                logger.error(
                    f"Error in mock voice worker: {e}",
                    exc_info=True  # Full stack trace
                )
    
    def _handle_speak_event(self, event: Event) -> None:
        """Gestisce SPEAK scrivendo nel log"""
        text = str(event.content)
        logger.info(f"🔊 [MOCK VOICE] SPEAK: {text}")
