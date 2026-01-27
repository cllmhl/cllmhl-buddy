from dataclasses import dataclass, field
from typing import Optional
import threading

@dataclass
class BuddyState:
    """
    A singleton class to hold the global state of Buddy.
    """
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    is_speaking: threading.Event = field(default_factory=threading.Event)

# Global state instance
global_state = BuddyState()
