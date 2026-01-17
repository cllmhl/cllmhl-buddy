"""
Output Adapters (Secondary Adapters)
Adattatori che eseguono azioni nel mondo esterno in risposta agli eventi.
"""

from .voice_output import JabraVoiceOutput, MockVoiceOutput
from .led_output import GPIOLEDOutput, MockLEDOutput
from .database_output import DatabaseOutput, MockDatabaseOutput
from .archivist_output import ArchivistOutput, MockArchivistOutput

# Auto-register nel Factory
from adapters.factory import AdapterFactory

AdapterFactory.register_output("JabraVoiceOutput", JabraVoiceOutput)
AdapterFactory.register_output("MockVoiceOutput", MockVoiceOutput)
AdapterFactory.register_output("GPIOLEDOutput", GPIOLEDOutput)
AdapterFactory.register_output("MockLEDOutput", MockLEDOutput)
AdapterFactory.register_output("DatabaseOutput", DatabaseOutput)
AdapterFactory.register_output("MockDatabaseOutput", MockDatabaseOutput)
AdapterFactory.register_output("ArchivistOutput", ArchivistOutput)
AdapterFactory.register_output("MockArchivistOutput", MockArchivistOutput)

__all__ = [
    'JabraVoiceOutput',
    'MockVoiceOutput',
    'GPIOLEDOutput',
    'MockLEDOutput',
    'DatabaseOutput',
    'MockDatabaseOutput',
    'ArchivistOutput',
    'MockArchivistOutput'
]
