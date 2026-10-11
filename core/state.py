from dataclasses import dataclass, field
import time
from typing import Optional
import threading

from sympy import true

@dataclass
class BuddyState:
    """
    A singleton class to hold the global state of Buddy.
    """
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    luminance: Optional[int] = None
    is_door_closed: bool = True
    last_door_closed: float = field(default_factory=time.time)
    last_presence: Optional[float] = None
    last_absence: float = field(default_factory=time.time)
    last_conversation_start: Optional[float] = None # Valorizzato da _handle_wakeword del brain
    last_conversation_end: Optional[float] = None # Valorizzato da _handle_conversation_end del brain
    is_light_on: Optional[bool] = None
    is_speaking: threading.Event = field(default_factory=threading.Event)
    is_thinking: threading.Event = field(default_factory=threading.Event)

    def isSomebodyAtHome(self) -> bool:
        """
        Determina se c'è qualcuno in casa ragionando su porta, presenza e assenza.
        """
        if self.last_presence is None:
            # Nessuna attività mai rilevata finora
            return False

        # Se l'ultima presenza è più recente dell'ultima assenza, allora c'è qualcuno in casa
        if self.last_presence > self.last_absence:
            return True

        # Se arrivo qui l'ultima assenza è più recente dell'ultima presenza ma potrei essere fermo o in bagno, 
        # controllo quindi se dopo la chiusura della porta c'è stata presenza: last_presence > last_door_closed.
        # ATTENZIONE: quando chiudo la porta, per diversi secondi il radar rileva ancora presenza, uso 20 secondi come margine di sicurezza.
        if (self.last_presence - self.last_door_closed) > 20.0:
            return True

        # nessuno è in casa
        return False

# Global state instance
global_state = BuddyState()