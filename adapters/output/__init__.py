"""
Output Adapters (Secondary Adapters)
Adattatori che eseguono azioni nel mondo esterno in risposta agli eventi.

Le classi vengono automaticamente rese disponibili al factory tramite __all__.
"""

from .voice_output import JabraVoiceOutput, MockVoiceOutput
from .led_output import GPIOLEDOutput, MockLEDOutput
from .database_output import DatabaseOutput, MockDatabaseOutput
from .archivist_output import ArchivistOutput, MockArchivistOutput
from .console_output import ConsoleOutput, MockConsoleOutput
from .pipe_output import PipeOutputAdapter

__all__ = [
    'JabraVoiceOutput',
    'MockVoiceOutput',
    'GPIOLEDOutput',
    'MockLEDOutput',
    'DatabaseOutput',
    'MockDatabaseOutput',
    'ArchivistOutput',
    'MockArchivistOutput',
    'ConsoleOutput',
    'MockConsoleOutput',
    'PipeOutputAdapter'
]
