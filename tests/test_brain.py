"""
Unit Tests for BuddyBrain
"""

import unittest
from unittest.mock import MagicMock, patch
import time

from core.brain import BuddyBrain
from core.events import Event, InputEventType, OutputEventType, EventPriority
from core.commands import AdapterCommand

# Mock config for the brain
MOCK_BRAIN_CONFIG = {
    "model_id": "gemini-pro",
    "system_instruction": "You are a helpful assistant.",
    "temperature": 0.7,
    "archivist_interval": 300  # 5 minutes
}

class TestBuddyBrain(unittest.TestCase):

    def setUp(self):
        """Set up a new BuddyBrain instance for each test."""
        # Mock the genai client
        self.mock_genai_client = MagicMock()
        self.mock_chat_session = MagicMock()
        self.mock_genai_client.chats.create.return_value = self.mock_chat_session
        
        # Patch the genai Client instantiation
        patcher = patch('google.genai.Client', return_value=self.mock_genai_client)
        self.addCleanup(patcher.stop)
        patcher.start()

        self.brain = BuddyBrain(api_key="fake_api_key", config=MOCK_BRAIN_CONFIG)

    def test_handle_user_speech(self):
        """Test that user speech generates correct output events and commands."""
        # Mock the LLM response
        self.mock_chat_session.send_message.return_value = MagicMock(text="This is a test response.")

        input_text = "Hello, Buddy"
        input_event = Event(
            priority=EventPriority.HIGH,
            type=InputEventType.USER_SPEECH,
            content=input_text,
            source="voice"
        )

        output_events, adapter_commands = self.brain.process_event(input_event)

        # 1. Check that send_message was called with the correct text
        self.mock_chat_session.send_message.assert_called_once_with(input_text)

        # 2. Check for SAVE_HISTORY event for the user message
        self.assertTrue(any(
            evt.type == OutputEventType.SAVE_HISTORY and evt.content["role"] == "user"
            for evt in output_events
        ))

        # 3. Check for SAVE_HISTORY event for the model response
        self.assertTrue(any(
            evt.type == OutputEventType.SAVE_HISTORY and evt.content["role"] == "model"
            for evt in output_events
        ))

        # 4. Check for SPEAK event
        self.assertTrue(any(
            evt.type == OutputEventType.SPEAK and evt.content == "This is a test response."
            for evt in output_events
        ))

        # 5. Check for WAKEWORD_LISTEN_START command
        self.assertIn(AdapterCommand.WAKEWORD_LISTEN_START, adapter_commands)

    def test_handle_wakeword(self):
        """Test that a wakeword event triggers the correct commands and LED event."""
        input_event = Event(
            priority=EventPriority.HIGH,
            type=InputEventType.WAKEWORD,
            content=None,
            source="voice"
        )

        output_events, adapter_commands = self.brain.process_event(input_event)

        # Check for LED_CONTROL event
        self.assertTrue(any(
            evt.type == OutputEventType.LED_CONTROL and evt.metadata and evt.metadata.get("command") == "on"
            for evt in output_events
        ))

        # Check for correct commands
        self.assertIn(AdapterCommand.WAKEWORD_LISTEN_STOP, adapter_commands)
        self.assertIn(AdapterCommand.VOICE_INPUT_START, adapter_commands)

    def test_handle_invalid_adapter_command(self):
        """Test that an invalid adapter command raises a ValueError."""
        input_event = Event(
            priority=EventPriority.CRITICAL,
            type=InputEventType.ADAPTER_COMMAND,
            content="INVALID_COMMAND_NAME"
        )
        
        with self.assertRaises(ValueError):
            self.brain.process_event(input_event)

    def test_archivist_trigger(self):
        """Test that the archivist is triggered after the interval."""
        # Set the last archivist time to be in the past
        self.brain.last_archivist_time = time.time() - self.brain.archivist_interval - 1

        input_event = Event(
            priority=EventPriority.NORMAL,
            type=InputEventType.USER_SPEECH,
            content="Some text to trigger processing"
        )
        
        self.mock_chat_session.send_message.return_value = MagicMock(text="A response")

        output_events, _ = self.brain.process_event(input_event)

        # Check for the DISTILL_MEMORY event
        self.assertTrue(any(
            evt.type == OutputEventType.DISTILL_MEMORY for evt in output_events
        ))

    def test_no_archivist_trigger(self):
        """Test that the archivist is NOT triggered before the interval."""
        # Set the last archivist time to now
        self.brain.last_archivist_time = time.time()

        input_event = Event(
            priority=EventPriority.NORMAL,
            type=InputEventType.USER_SPEECH,
            content="Some text"
        )
        
        self.mock_chat_session.send_message.return_value = MagicMock(text="A response")

        output_events, _ = self.brain.process_event(input_event)

        # Check that the DISTILL_MEMORY event is NOT present
        self.assertFalse(any(
            evt.type == OutputEventType.DISTILL_MEMORY for evt in output_events
        ))

if __name__ == '__main__':
    unittest.main()
