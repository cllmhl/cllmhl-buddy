"""
Input Adapters (Primary Adapters)
Adattatori che ricevono input dal mondo esterno e li trasformano in eventi.
"""

from .voice_input import JabraVoiceInput, MockVoiceInput
from .radar_input import RadarInput, MockRadarInput
from .temperature_input import TemperatureInput, MockTemperatureInput
from .direct_output_input import DirectOutputInput

# Auto-register nel Factory
from adapters.factory import AdapterFactory

AdapterFactory.register_input("JabraVoiceInput", JabraVoiceInput)
AdapterFactory.register_input("MockVoiceInput", MockVoiceInput)
AdapterFactory.register_input("RadarInput", RadarInput)
AdapterFactory.register_input("MockRadarInput", MockRadarInput)
AdapterFactory.register_input("TemperatureInput", TemperatureInput)
AdapterFactory.register_input("MockTemperatureInput", MockTemperatureInput)
AdapterFactory.register_input("DirectOutputInput", DirectOutputInput)

__all__ = [
    'JabraVoiceInput',
    'MockVoiceInput',
    'RadarInput',
    'MockRadarInput',
    'TemperatureInput',
    'MockTemperatureInput',
    'DirectOutputInput'
]
