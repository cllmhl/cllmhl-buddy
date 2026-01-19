"""
Adapter command definitions for Brain → Adapter control flow.

Commands are semantic instructions that the Brain can issue to control adapter state.
All adapters receive all commands via broadcast (synchronous), and each adapter
decides whether to handle or ignore them based on their capabilities.
"""

from enum import Enum


class AdapterCommand(str, Enum):
    """
    Semantic commands for adapter state control.
    
    Naming convention: <DOMAIN>_<ACTION>
    - DOMAIN: Wakeword detection, voice I/O, sensors, etc.
    - ACTION: What should happen (STOP, START, PAUSE, RESUME, etc.)
    
    Brain produces these; adapters declare which they support.
    """
    
    # Wakeword detection control
    WAKEWORD_LISTEN_START = "wakeword_listen_start"
    WAKEWORD_LISTEN_STOP = "wakeword_listen_stop"
    
    # Voice output control
    VOICE_OUTPUT_STOP = "voice_output_stop"
    VOICE_OUTPUT_RESUME = "voice_output_resume"
    
    # Voice input control
    VOICE_INPUT_START = "voice_input_start"
    VOICE_INPUT_STOP = "voice_input_stop"
    
    # Sensor control (generic)
    SENSOR_PAUSE = "sensor_pause"
    SENSOR_RESUME = "sensor_resume"
    
    # LED visual feedback
    LED_LISTENING = "led_listening"
    LED_THINKING = "led_thinking"
    LED_SPEAKING = "led_speaking"
    LED_IDLE = "led_idle"
