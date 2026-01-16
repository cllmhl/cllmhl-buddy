"""
Input Adapters (Primary Adapters)
Adattatori che ricevono input dal mondo esterno e li trasformano in eventi.
"""

from .voice_input import JabraVoiceInput, MockVoiceInput
from .radar_input import RadarInput, MockRadarInput
from .temperature_input import TemperatureInput, MockTemperatureInput

# Auto-register nel Factory
from adapters.factory import AdapterFactory
AdapterFactory.register_input("jabra", JabraVoiceInput)
AdapterFactory.register_input("mock_voice", MockVoiceInput)
AdapterFactory.register_input("radar", RadarInput)
AdapterFactory.register_input("mock_radar", MockRadarInput)
AdapterFactory.register_input("temperature", TemperatureInput)
AdapterFactory.register_input("mock_temperature", MockTemperatureInput)

__all__ = [
    'JabraVoiceInput',
    'MockVoiceInput',
    'RadarInput',
    'MockRadarInput',
    'TemperatureInput',
    'MockTemperatureInput'
]
