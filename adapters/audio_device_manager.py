"""
Audio Device Manager - Coordinamento device condivisi (Jabra)
Gestisce l'accesso esclusivo a device audio usati sia per input che output.
"""

import logging
import threading
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


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
    
    pa = pyaudio.PyAudio()
    jabra_index = None
    
    logger.info("Available PyAudio input devices:")
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        max_channels = int(info.get('maxInputChannels', 0))
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


class AudioDeviceState(Enum):
    """Stati del device audio"""
    IDLE = "idle"           # Device libero
    LISTENING = "listening" # Microfono attivo (input)
    SPEAKING = "speaking"   # Speaker attivo (output)


class AudioDeviceManager:
    """
    Gestisce accesso esclusivo a device audio condivisi.
    
    Problema risolto:
    - Jabra è sia input (mic) che output (speaker)
    - Quando parla (output), non deve ascoltare (input)
    - Quando ascolta (input), non deve parlare (output)
    
    Soluzione:
    - Lock per accesso esclusivo
    - State machine IDLE → LISTENING/SPEAKING → IDLE
    - Event per notificare cambio stato
    """
    
    def __init__(self, device_name: str = "jabra"):
        """
        Args:
            device_name: Nome identificativo del device
        """
        self.device_name = device_name
        self.state = AudioDeviceState.IDLE
        
        # Lock per thread-safety
        self._lock = threading.Lock()
        
        # Events per notifiche
        self.state_changed = threading.Event()
        self.is_speaking = threading.Event()  # Compatibility with old code
        
        logger.info(f"🎤 AudioDeviceManager initialized for '{device_name}'")
    
    def request_input(self, timeout: Optional[float] = None) -> bool:
        """
        Richiede accesso al device per INPUT (microfono).
        
        Args:
            timeout: Timeout in secondi (None = blocca indefinitamente)
            
        Returns:
            True se accesso concesso, False se timeout/occupato
        """
        with self._lock:
            # Se sta parlando, non possiamo ascoltare
            if self.state == AudioDeviceState.SPEAKING:
                logger.warning(f"🎤 Device BUSY: Cannot accept input while SPEAKING")
                return False
            
            # Se già in listening o idle, ok
            if self.state in [AudioDeviceState.IDLE, AudioDeviceState.LISTENING]:
                self.state = AudioDeviceState.LISTENING
                logger.debug(f"🎤 Input access granted (state: {self.state.value})")
                return True
            
            return False
    
    def request_output(self, timeout: Optional[float] = None) -> bool:
        """
        Richiede accesso al device per OUTPUT (speaker).
        
        Args:
            timeout: Timeout in secondi (None = blocca indefinitamente)
            
        Returns:
            True se accesso concesso, False se timeout/occupato
        """
        with self._lock:
            # Se sta ascoltando, dobbiamo interrompere
            if self.state == AudioDeviceState.LISTENING:
                logger.debug(f"🔊 Interrupting LISTENING for SPEAKING")
            
            # Imposta stato SPEAKING
            self.state = AudioDeviceState.SPEAKING
            self.is_speaking.set()  # Notifica listeners
            self.state_changed.set()
            
            logger.debug(f"🔊 Output access granted (state: {self.state.value})")
            return True
    
    def release(self) -> None:
        """Rilascia il device (torna IDLE)"""
        with self._lock:
            old_state = self.state
            self.state = AudioDeviceState.IDLE
            
            # Clear flags
            self.is_speaking.clear()
            self.state_changed.clear()
            
            logger.debug(f"✅ Device released ({old_state.value} → {self.state.value})")
    
    def wait_until_idle(self, timeout: Optional[float] = None) -> bool:
        """
        Aspetta che il device torni IDLE.
        
        Args:
            timeout: Timeout in secondi (None = blocca indefinitamente)
            
        Returns:
            True se device è IDLE, False se timeout
        """
        start_time = None
        if timeout is not None:
            import time
            start_time = time.time()
        
        while True:
            with self._lock:
                if self.state == AudioDeviceState.IDLE:
                    return True
            
            # Check timeout
            if timeout is not None and start_time is not None:
                if time.time() - start_time > timeout:
                    return False
            
            # Wait a bit
            self.state_changed.wait(timeout=0.1)
    
    def get_state(self) -> AudioDeviceState:
        """Ritorna lo stato corrente del device"""
        with self._lock:
            return self.state
    
    def is_busy(self) -> bool:
        """Controlla se il device è occupato"""
        with self._lock:
            return self.state != AudioDeviceState.IDLE


# Singleton globale per Jabra
_jabra_manager: Optional[AudioDeviceManager] = None


def get_jabra_manager() -> AudioDeviceManager:
    """
    Ottiene il manager Jabra (singleton).
    
    Returns:
        Istanza singleton di AudioDeviceManager per Jabra
    """
    global _jabra_manager
    
    if _jabra_manager is None:
        _jabra_manager = AudioDeviceManager("jabra")
    
    return _jabra_manager
