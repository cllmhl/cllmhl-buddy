"""
Output Adapters (Secondary Adapters)
Adattatori che eseguono azioni nel mondo esterno in risposta agli eventi.
"""

from .voice_output import JabraVoiceOutput, MockVoiceOutput
from .led_output import GPIOLEDOutput, MockLEDOutput
from .database_output import DatabaseOutput
from .log_output import LogOutput

# Auto-register nel Factory
from adapters.factory import AdapterFactory

AdapterFactory.register_output("jabra", JabraVoiceOutput)
AdapterFactory.register_output("log", MockVoiceOutput)
AdapterFactory.register_output("gpio", GPIOLEDOutput)
AdapterFactory.register_output("mock", MockLEDOutput)
AdapterFactory.register_output("real", DatabaseOutput)
AdapterFactory.register_output("file", LogOutput)

__all__ = [
    'JabraVoiceOutput',
    'MockVoiceOutput',
    'GPIOLEDOutput',
    'MockLEDOutput',
    'DatabaseOutput',
    'LogOutput'
]
