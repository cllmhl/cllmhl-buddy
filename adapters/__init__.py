"""
Adapters - Primary e Secondary Adapters per l'architettura esagonale
"""

from .ports import (
    # Base classes
    InputPort, OutputPort, AudioDevicePort,
    # Output specializations
    VoiceOutputPort, LEDOutputPort, DatabaseOutputPort,
    # Input specializations
    VoiceInputPort, SensorInputPort, RadarInputPort, TemperatureInputPort
)
from .factory import AdapterFactory

# Import modules to trigger auto-registration
from . import input
from . import output

__all__ = [
    'InputPort',
    'OutputPort',
    'AudioDevicePort',
    'AdapterFactory'
]
