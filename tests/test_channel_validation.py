"""
Test validazione channel_type degli OutputPort
"""

import pytest
from adapters.output.voice_output import MockVoiceOutput
from adapters.output.led_output import MockLEDOutput
from adapters.output.database_output import MockDatabaseOutput
from core.events import OutputChannel


class TestChannelValidation:
    """Test che gli adapter dichiarino correttamente il channel_type"""
    
    def test_voice_adapter_has_correct_channel_type(self):
        """Voice adapter deve dichiarare OutputChannel.VOICE"""
        adapter = MockVoiceOutput("test_voice", {})
        assert adapter.channel_type == OutputChannel.VOICE
    
    def test_led_adapter_has_correct_channel_type(self):
        """LED adapter deve dichiarare OutputChannel.LED"""
        adapter = MockLEDOutput("test_led", {})
        assert adapter.channel_type == OutputChannel.LED
    
    def test_database_adapter_has_correct_channel_type(self):
        """Database adapter deve dichiarare OutputChannel.DATABASE"""
        adapter = MockDatabaseOutput("test_db", {})
        assert adapter.channel_type == OutputChannel.DATABASE
    
    def test_mismatched_channel_types_are_different(self):
        """Adapter di diverso tipo hanno channel_type diversi"""
        voice = MockVoiceOutput("voice", {})
        led = MockLEDOutput("led", {})
        database = MockDatabaseOutput("db", {})
        
        assert voice.channel_type != led.channel_type
        assert voice.channel_type != database.channel_type
        assert led.channel_type != database.channel_type
    
    def test_all_output_channels_covered(self):
        """Verifica che tutti i canali abbiano un adapter corrispondente"""
        from adapters.output import MockVoiceOutput, MockLEDOutput, MockDatabaseOutput, MockArchivistOutput, MockConsoleOutput
        
        voice = MockVoiceOutput("voice", {})
        led = MockLEDOutput("led", {})
        database = MockDatabaseOutput("db", {})
        archivist = MockArchivistOutput("archivist", {})
        console = MockConsoleOutput("console", {})
        
        adapter_channels = {
            voice.channel_type, 
            led.channel_type, 
            database.channel_type,
            archivist.channel_type,
            console.channel_type
        }
        all_channels = set(OutputChannel)
        
        assert adapter_channels == all_channels, \
            f"Missing adapters for channels: {all_channels - adapter_channels}"
