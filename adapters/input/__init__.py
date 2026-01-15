"""
Input Adapters (Primary Adapters)
Adattatori che ricevono input dal mondo esterno e li trasformano in eventi.
"""

from .keyboard_input import KeyboardInput
from .pipe_input import PipeInput

# Auto-register nel Factory
from adapters.factory import AdapterFactory

AdapterFactory.register_input("stdin", KeyboardInput)
AdapterFactory.register_input("pipe", PipeInput)

__all__ = [
    'KeyboardInput',
    'PipeInput'
]
