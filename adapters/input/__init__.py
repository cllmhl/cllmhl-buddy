"""
Input Adapters (Primary Adapters)
Adattatori che ricevono input dal mondo esterno e li trasformano in eventi.

Le classi vengono automaticamente rese disponibili al factory tramite __all__.
"""

from .voice_input import JabraVoiceInput, MockVoiceInput
from .radar_input import RadarInput, MockRadarInput
from .temperature_input import TemperatureInput, MockTemperatureInput
from .direct_output_input import DirectOutputInput

__all__ = [
    'JabraVoiceInput',
    'MockVoiceInput',
    'RadarInput',
    'MockRadarInput',
    'TemperatureInput',
    'MockTemperatureInput',
    'DirectOutputInput'
]
