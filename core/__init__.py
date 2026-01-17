"""
Buddy Core - Hexagonal Architecture
Logica di business pura, zero dipendenze esterne.
"""

from .events import (
    Event, EventType, EventPriority, OutputChannel,
    build_event_routing_from_adapters,
    create_input_event, create_output_event
)
from .event_router import EventRouter
from .brain import BuddyBrain

__all__ = [
    'Event',
    'EventType', 
    'EventPriority',
    'OutputChannel',
    'build_event_routing_from_adapters',
    'create_input_event',
    'create_output_event',
    'EventRouter',
    'BuddyBrain'
]
