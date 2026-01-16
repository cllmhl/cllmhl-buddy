"""
Adapters - Primary e Secondary Adapters per l'architettura esagonale
"""

from .ports import InputPort, OutputPort, AudioDevicePort
from .factory import AdapterFactory
from .adapter_types import InputAdapterType, OutputAdapterType

# Import modules to trigger auto-registration
from . import input
from . import output

__all__ = [
    'InputPort',
    'OutputPort',
    'AudioDevicePort',
    'AdapterFactory',
    'InputAdapterType',
    'OutputAdapterType'
]
