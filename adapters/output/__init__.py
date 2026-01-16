"""
Output Adapters (Secondary Adapters)
Adattatori che eseguono azioni nel mondo esterno in risposta agli eventi.
"""

from .voice_output import JabraVoiceOutput, MockVoiceOutput
from .led_output import GPIOLEDOutput, MockLEDOutput
from .database_output import DatabaseOutput, MockDatabaseOutput

# Auto-register nel Factory
from adapters.factory import AdapterFactory
from adapters.adapter_types import OutputAdapterType

AdapterFactory.register_output(OutputAdapterType.VOICE.value, JabraVoiceOutput)
AdapterFactory.register_output(OutputAdapterType.MOCK_VOICE.value, MockVoiceOutput)
AdapterFactory.register_output(OutputAdapterType.LED.value, GPIOLEDOutput)
AdapterFactory.register_output(OutputAdapterType.MOCK_LED.value, MockLEDOutput)
AdapterFactory.register_output(OutputAdapterType.DATABASE.value, DatabaseOutput)
AdapterFactory.register_output(OutputAdapterType.MOCK_DATABASE.value, MockDatabaseOutput)

__all__ = [
    'JabraVoiceOutput',
    'MockVoiceOutput',
    'GPIOLEDOutput',
    'MockLEDOutput',
    'DatabaseOutput',
    'MockDatabaseOutput'
]
