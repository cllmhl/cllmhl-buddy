"""
Adapters - Primary e Secondary Adapters per l'architettura esagonale
"""

from .ports import InputPort, OutputPort, AudioDevicePort
from .factory import AdapterFactory

__all__ = [
    'InputPort',
    'OutputPort',
    'AudioDevicePort',
    'AdapterFactory'
]
