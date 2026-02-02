from dataclasses import dataclass, field
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
    last_presence: Optional[float] = None
    last_absence: Optional[float] = None
    last_conversation_start: Optional[float] = None # Valorizzato da _handle_wakeword del brain
    last_conversation_end: Optional[float] = None # Valorizzato da _handle_conversation_end del brain
    is_light_on: bool = True
    is_speaking: threading.Event = field(default_factory=threading.Event)

# Global state instance
global_state = BuddyState()
