from dataclasses import dataclass
from typing import Optional

@dataclass
class BuddyState:
    """
    A singleton class to hold the global state of Buddy.
    """
    temperature: Optional[float] = None
    humidity: Optional[float] = None

# Global state instance
global_state = BuddyState()
