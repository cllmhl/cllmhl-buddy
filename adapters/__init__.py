"""
Adapters - Primary e Secondary Adapters per l'architettura esagonale
"""

from .ports import InputPort, OutputPort, AdapterPort
from .factory import AdapterFactory

# Import modules to trigger auto-registration
from . import input
from . import output

__all__ = [
    'AdapterPort',
    'InputPort',
    'OutputPort',
    'AdapterFactory'
]
