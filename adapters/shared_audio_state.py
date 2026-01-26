import threading

import os
import logging
from typing import Optional
# FIXME: Timer fine dialogo Jabra
is_speaking = threading.Event() 
logger = logging.getLogger(__name__)


class SuppressStream:
    """Sopprime stderr temporaneamente per silenziare ALSA warnings"""
    def __enter__(self):
        self.err_null = os.open(os.devnull, os.O_WRONLY)
        self.old_err = os.dup(2)
        os.dup2(self.err_null, 2)
        return self
    
    def __exit__(self, *args):
        os.dup2(self.old_err, 2)
        os.close(self.err_null)
        os.close(self.old_err)


def find_jabra_pvrecorder() -> Optional[int]:
    """
    Trova l'indice del dispositivo Jabra in PvRecorder.
    
    Returns:
        Indice del device Jabra, o None se non trovato
        
    Raises:
        ImportError: Se PvRecorder non è disponibile
    """
    try:
        from pvrecorder import PvRecorder
    except ImportError:
        logger.error("PvRecorder not available")
        raise ImportError("PvRecorder required for Jabra detection")
    
    available_devices = PvRecorder.get_available_devices()
    logger.info("Available PvRecorder audio devices:")
    
    jabra_index = None
    for i, device in enumerate(available_devices):
        logger.info(f"  PvRecorder Index {i}: {device}")
        if "Jabra" in device:
            jabra_index = i
            logger.info(f"✅ Jabra found in PvRecorder at index {i}: {device}")
    
    if jabra_index is None:
        logger.error("❌ Jabra device not found in PvRecorder device list")
    
    return jabra_index


def find_jabra_pyaudio() -> Optional[int]:
    """
    Trova l'indice del dispositivo Jabra in PyAudio (per speech_recognition).
    
    Returns:
        Indice del device Jabra, o None se non trovato
        
    Raises:
        ImportError: Se PyAudio non è disponibile
    """
    try:
        import pyaudio
    except ImportError:
        logger.error("PyAudio not available")
        raise ImportError("PyAudio required for Jabra detection")
    
    # Sopprime stderr per evitare ALSA warnings
    with SuppressStream():
        pa = pyaudio.PyAudio()
        jabra_index = None
        
        logger.info("Available PyAudio input devices:")
        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            max_channels = int(info['maxInputChannels'])  # Fail-fast: must be present
            device_name = str(info['name'])
            
            if max_channels > 0:
                logger.info(f"  PyAudio Index {i}: {device_name} (channels={max_channels})")
                if 'Jabra' in device_name:
                    jabra_index = i
                    logger.info(f"✅ Jabra found in PyAudio at index {i}: {device_name}")
        
        pa.terminate()
    
    if jabra_index is None:
        logger.error("❌ Jabra device not found in PyAudio device list")
    
    return jabra_index


def find_jabra_alsa() -> Optional[str]:
    """
    Trova il device ALSA del Jabra (per output audio).
    
    Returns:
        Device string tipo 'plughw:2,0', o None se non trovato
    """
    import subprocess
    
    try:
        # aplay -l per listare i device
        result = subprocess.run(
            ['aplay', '-l'],
            capture_output=True,
            text=True,
            check=True
        )
        
        lines = result.stdout.split('\n')
        logger.info("Available ALSA playback devices:")
        
        for line in lines:
            logger.debug(f"  {line}")
            if 'Jabra' in line or 'SPEAK' in line:
                # Esempio: "card 2: S410 [Jabra SPEAK 410 USB], device 0: USB Audio [USB Audio]"
                if 'card' in line and 'device' in line:
                    parts = line.split(',')
                    card_part = parts[0].split('card')[1].strip().split(':')[0]
                    device_part = parts[1].split('device')[1].strip().split(':')[0]
                    device_str = f"plughw:{card_part},{device_part}"
                    logger.info(f"✅ Jabra found in ALSA: {device_str}")
                    return device_str
        
        logger.error("❌ Jabra device not found in ALSA device list")
        return None
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to execute aplay: {e}")
        return None
    except Exception as e:
        logger.error(f"Error detecting Jabra ALSA device: {e}")
        return None
