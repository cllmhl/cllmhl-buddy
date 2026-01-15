"""
Audio Device Manager - Coordinamento device condivisi (Jabra)
Gestisce l'accesso esclusivo a device audio usati sia per input che output.
"""

import logging
import threading
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


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
                logger.debug(f"🎤 Device busy (SPEAKING), input denied")
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
            if timeout is not None:
                import time
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
