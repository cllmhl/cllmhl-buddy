"""
Buddy Core - Hexagonal Architecture
Logica di business pura, zero dipendenze esterne.
"""

from .events import (
    Event, InputEventType, OutputEventType, EventPriority,
    create_input_event, create_output_event
)
from .event_router import EventRouter
from .brain import BuddyBrain

__all__ = [
    'Event',
    'InputEventType',
    'OutputEventType',
    'EventPriority',
    'create_input_event',
    'create_output_event',
    'EventRouter',
    'BuddyBrain'
]
