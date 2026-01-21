"""
Input Adapters (Primary Adapters)
Adattatori che ricevono input dal mondo esterno e li trasformano in eventi.

Le classi vengono automaticamente rese disponibili al factory tramite __all__.
"""

from .ear_input import EarInput
from .radar_input import RadarInput
from .temperature_input import TemperatureInput
from .pipe_input import PipeInputAdapter
from .wakeword_input import WakewordInput

__all__ = [
    'EarInput',
    'RadarInput',
    'TemperatureInput',
    'PipeInputAdapter',
    'WakewordInput'
]
