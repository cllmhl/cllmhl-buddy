"""
Adapter Types - Enum per identificatori adapter
"""

from enum import Enum


class InputAdapterType(Enum):
    """Tipi di Input Adapters disponibili"""
    EAR = "jabra"
    MOCK_EAR = "mock_ear"
    RADAR = "radar"
    MOCK_RADAR = "mock_radar"
    TEMPERATURE = "temperature"
    MOCK_TEMPERATURE = "mock_temperature"


class OutputAdapterType(Enum):
    """Tipi di Output Adapters disponibili"""
    VOICE = "jabra"
    MOCK_VOICE = "mock_voice"
    LED = "led"
    MOCK_LED = "mock_led"
    DATABASE = "db"
    MOCK_DATABASE = "mock_db"
