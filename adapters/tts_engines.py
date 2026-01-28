"""
TTS Engines - Motori di sintesi vocale
Implementazioni concrete dei diversi motori TTS supportati da Buddy
"""

import os
import time
import logging
import subprocess
from abc import ABC, abstractmethod
from typing import Optional

from gtts import gTTS
from google.cloud import texttospeech

logger = logging.getLogger(__name__)


class TTSEngine(ABC):
    """Classe base astratta per motori TTS - Solo sintesi, NO playback"""
    
    def __init__(self, voice_name: str):
        """
        Args:
            voice_name: Nome della voce da usare
        
        Raises:
            ValueError: Se configurazione non valida
            FileNotFoundError: Se dipendenze mancanti
        """
        self.voice_name = voice_name
        self._validate_config()
    
    @abstractmethod
    def _validate_config(self) -> None:
        """Valida configurazione specifica del motore (fail-fast)
        
        Raises:
            ValueError: Se configurazione non valida
            FileNotFoundError: Se dipendenze mancanti
        """
        pass
    
    @abstractmethod
    def synthesize(self, text: str) -> str:
        """Sintetizza il testo e restituisce il path del file audio
        
        Args:
            text: Testo da sintetizzare
        
        Returns:
            Path assoluto del file audio generato (temporary file)
        
        Raises:
            Exception: Se sintesi fallisce
        """
        pass


class GTTSEngine(TTSEngine):
    """Motore TTS basato su Google gTTS (cloud, gratuito)"""
    
    def _validate_config(self) -> None:
        """Nessuna validazione necessaria per gTTS"""
        logger.info(f"✅ gTTS engine initialized (voice: {self.voice_name})")
    
    def synthesize(self, text: str) -> str:
        """Sintetizza con gTTS e restituisce filename"""
        try:
            logger.debug(f"Generating gTTS for: {text[:50]}...")
            tts = gTTS(text=text, lang='it')
            filename = f"/tmp/buddy_tts_{time.time()}.mp3"
            tts.save(filename)
            logger.debug(f"TTS saved to {filename}")
            return filename
        
        except Exception as e:
            logger.error(f"❌ gTTS synthesis error: {e}", exc_info=True)
            raise


class PiperEngine(TTSEngine):
    """Motore TTS locale basato su Piper"""
    
    def __init__(self, voice_name: str):
        # Setup paths prima della validazione
        home = os.path.expanduser("~")
        self.piper_base_path = os.path.join(home, "buddy_tools/piper")
        self.piper_binary = os.path.join(self.piper_base_path, "piper/piper")
        
        # Voice configuration
        self.voice_map = {
            "paola": {"file": "it_IT-paola-medium.onnx", "speed": "1.0"},
            "riccardo": {"file": "it_IT-riccardo-x_low.onnx", "speed": "1.1"}
        }
        
        super().__init__(voice_name)
    
    def _validate_config(self) -> None:
        """Valida presenza Piper binary e modello voce"""
        # Check binary
        if not os.path.isfile(self.piper_binary):
            raise FileNotFoundError(
                f"Piper binary not found: {self.piper_binary}. "
                f"Install with: bash scripts/install_piper.sh"
            )
        
        # Check voice support
        if self.voice_name not in self.voice_map:
            raise ValueError(
                f"Voice '{self.voice_name}' not supported. "
                f"Available: {list(self.voice_map.keys())}"
            )
        
        # Setup voice config
        voice_config = self.voice_map[self.voice_name]
        self.piper_model = os.path.join(self.piper_base_path, voice_config["file"])
        self.piper_speed = voice_config["speed"]
        
        # Check model file
        if not os.path.isfile(self.piper_model):
            raise FileNotFoundError(
                f"Piper model not found: {self.piper_model}. "
                f"Download models from Piper releases."
            )
        
        logger.info(f"✅ Piper engine initialized (voice: {self.voice_name}, model: {self.piper_model})")
    
    def synthesize(self, text: str) -> str:
        """Sintetizza con Piper e restituisce filename WAV"""
        try:
            filename = f"/tmp/buddy_tts_{time.time()}.wav"
            
            piper_cmd = [
                self.piper_binary,
                "--model", self.piper_model,
                "--length_scale", self.piper_speed,
                "--output_file", filename
            ]
            
            # Esegui Piper per generare WAV
            result = subprocess.run(
                piper_cmd,
                input=text.encode('utf-8'),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.decode() if result.stderr else "Unknown error"
                raise RuntimeError(f"Piper failed with return code {result.returncode}: {error_msg}")
            
            logger.debug(f"Piper TTS saved to {filename}")
            return filename
        
        except Exception as e:
            logger.error(f"❌ Piper synthesis error: {e}", exc_info=True)
            raise


class TextToSpeechEngine(TTSEngine):
    """Motore TTS basato su Google Cloud Text-to-Speech (cloud, premium)"""
    
    def _validate_config(self) -> None:
        """Valida credenziali Google Cloud"""
        # Check credentials
        if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
            raise ValueError(
                "GOOGLE_APPLICATION_CREDENTIALS environment variable is not set. "
                "Set it to your service account JSON key path."
            )
        
        # Test client creation
        try:
            self.client = texttospeech.TextToSpeechClient()
        except Exception as e:
            raise ValueError(f"Failed to create TextToSpeech client: {e}")
        
        logger.info(f"✅ Google Cloud TextToSpeech engine initialized (voice: {self.voice_name})")
    
    def synthesize(self, text: str) -> str:
        """Sintetizza con Google Cloud TTS e restituisce filename"""
        try:
            # Synthesis request
            input_text = texttospeech.SynthesisInput(text=text)
            voice = texttospeech.VoiceSelectionParams(
                language_code="it-IT",
                name=self.voice_name,
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )
            
            logger.debug(f"Generating Cloud TTS for: {text[:50]}...")
            response = self.client.synthesize_speech(
                request={
                    "input": input_text,
                    "voice": voice,
                    "audio_config": audio_config
                }
            )
            
            # Save to temp file
            filename = f"/tmp/buddy_tts_{time.time()}.mp3"
            with open(filename, "wb") as out:
                out.write(response.audio_content)
            logger.debug(f"Cloud TTS saved to {filename}")
            
            return filename
        
        except Exception as e:
            logger.error(f"❌ Cloud TextToSpeech synthesis error: {e}", exc_info=True)
            raise


def create_tts_engine(tts_mode: str, voice_name: str) -> TTSEngine:
    """Factory per creare il motore TTS appropriato
    
    Args:
        tts_mode: Tipo di motore ('cloud', 'local', 'texttospeech')
        voice_name: Nome della voce
    
    Returns:
        Istanza del motore TTS
    
    Raises:
        ValueError: Se tts_mode non supportato
    """
    engines = {
        "cloud": GTTSEngine,
        "local": PiperEngine,
        "texttospeech": TextToSpeechEngine,
    }
    
    if tts_mode not in engines:
        raise ValueError(
            f"Unsupported tts_mode '{tts_mode}'. "
            f"Available: {list(engines.keys())}"
        )
    
    engine_class = engines[tts_mode]
    return engine_class(voice_name)
