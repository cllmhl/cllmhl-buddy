"""
Input Adapters (Primary Adapters)
Adattatori che ricevono input dal mondo esterno e li trasformano in eventi.
"""

from .voice_input import JabraVoiceInput, MockVoiceInput
from .radar_input import RadarInput, MockRadarInput
from .temperature_input import TemperatureInput, MockTemperatureInput

# Auto-register nel Factory
from adapters.factory import AdapterFactory
from adapters.adapter_types import InputAdapterType

AdapterFactory.register_input(InputAdapterType.VOICE.value, JabraVoiceInput)
AdapterFactory.register_input(InputAdapterType.MOCK_VOICE.value, MockVoiceInput)
AdapterFactory.register_input(InputAdapterType.RADAR.value, RadarInput)
AdapterFactory.register_input(InputAdapterType.MOCK_RADAR.value, MockRadarInput)
AdapterFactory.register_input(InputAdapterType.TEMPERATURE.value, TemperatureInput)
AdapterFactory.register_input(InputAdapterType.MOCK_TEMPERATURE.value, MockTemperatureInput)

__all__ = [
    'JabraVoiceInput',
    'MockVoiceInput',
    'RadarInput',
    'MockRadarInput',
    'TemperatureInput',
    'MockTemperatureInput'
]
