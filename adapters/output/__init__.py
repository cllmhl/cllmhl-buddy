"""
Output Adapters (Secondary Adapters)
Adattatori che eseguono azioni nel mondo esterno in risposta agli eventi.

Le classi vengono automaticamente rese disponibili al factory tramite __all__.
"""

from .voice_output import JabraVoiceOutput
from .led_output import GPIOLEDOutput
from .database_output import DatabaseOutput
from .archivist_output import ArchivistOutput
from .pipe_output import PipeOutputAdapter
from .log_output import LogOutput
from .tapo_output import TapoOutput

__all__ = [
    'JabraVoiceOutput',
    'GPIOLEDOutput',
    'DatabaseOutput',
    'ArchivistOutput',
    'PipeOutputAdapter',
    'LogOutput',
    'TapoOutput'
]
