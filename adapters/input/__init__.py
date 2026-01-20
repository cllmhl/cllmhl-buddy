"""
Input Adapters (Primary Adapters)
Adattatori che ricevono input dal mondo esterno e li trasformano in eventi.

Le classi vengono automaticamente rese disponibili al factory tramite __all__.
"""

from .ear_input import EarInput, MockEarInput
from .radar_input import RadarInput, MockRadarInput
from .temperature_input import TemperatureInput, MockTemperatureInput
from .pipe_input import PipeInputAdapter
from .direct_output_input import DirectOutputInput
from .wakeword_input import WakewordInput

__all__ = [
    'EarInput',
    'MockEarInput',
    'RadarInput',
    'MockRadarInput',
    'TemperatureInput',
    'MockTemperatureInput',
    'PipeInputAdapter',
    'DirectOutputInput',
    'WakewordInput'
]
