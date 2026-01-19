"""
Test che gli Output Adapter dichiarino correttamente gli eventi gestiti
"""

import pytest
from adapters.output.voice_output import JabraVoiceOutput, MockVoiceOutput
from adapters.output.led_output import GPIOLEDOutput, MockLEDOutput
from adapters.output.database_output import DatabaseOutput, MockDatabaseOutput
from core.events import OutputEventType


class TestOutputAdapterEvents:
    """Test che gli OutputAdapter dichiarino correttamente handled_events()"""
    
    def test_voice_output_declares_events(self):
        """Voice output adapter dichiara quali eventi gestisce"""
        events = JabraVoiceOutput.handled_events()
        assert OutputEventType.SPEAK in events
        assert len(events) == 1
        
        # Anche Mock deve dichiarare gli stessi eventi
        mock_events = MockVoiceOutput.handled_events()
        assert mock_events == events
    
    def test_led_output_declares_events(self):
        """LED output adapter dichiara quali eventi gestisce"""
        events = GPIOLEDOutput.handled_events()
        assert OutputEventType.LED_CONTROL in events
        assert len(events) == 1
        
        # Anche Mock deve dichiarare gli stessi eventi
        mock_events = MockLEDOutput.handled_events()
        assert mock_events == events
    
    def test_database_output_declares_events(self):
        """Database output adapter dichiara quali eventi gestisce"""
        events = DatabaseOutput.handled_events()
        assert OutputEventType.SAVE_HISTORY in events
        assert OutputEventType.SAVE_MEMORY in events
        assert len(events) == 2
        
        # Anche Mock deve dichiarare gli stessi eventi
        mock_events = MockDatabaseOutput.handled_events()
        assert mock_events == events
    
    def test_event_routing_built_from_adapter_declarations(self):
        """Il routing può essere costruito dinamicamente dalle dichiarazioni degli Adapter"""
        # Crea adapter mock per testare
        adapters = [
            MockVoiceOutput("test_voice", {}),
            MockLEDOutput("test_led", {}),
            MockDatabaseOutput("test_db", {})
        ]
        
        # Verifica che ogni adapter dichiari gli eventi corretti
        voice_events = MockVoiceOutput.handled_events()
        assert OutputEventType.SPEAK in voice_events
        
        led_events = MockLEDOutput.handled_events()
        assert OutputEventType.LED_CONTROL in led_events
        
        db_events = MockDatabaseOutput.handled_events()
        assert OutputEventType.SAVE_HISTORY in db_events
        assert OutputEventType.SAVE_MEMORY in db_events


class TestAdapterSignatures:
    """Test che gli Adapter abbiano signature chiare e complete"""
    
    def test_all_output_adapters_implement_handled_events(self):
        """Tutti gli OutputAdapter implementano handled_events()"""
        from adapters.output.console_output import ConsoleOutput, MockConsoleOutput
        from adapters.output.archivist_output import ArchivistOutput, MockArchivistOutput
        
        output_adapters = [
            JabraVoiceOutput, MockVoiceOutput,
            GPIOLEDOutput, MockLEDOutput,
            DatabaseOutput, MockDatabaseOutput,
            ConsoleOutput, MockConsoleOutput,
            ArchivistOutput, MockArchivistOutput
        ]
        
        for adapter_class in output_adapters:
            assert hasattr(adapter_class, 'handled_events'), \
                f"{adapter_class.__name__} must implement handled_events()"
            
            events = adapter_class.handled_events()
            assert len(events) > 0, \
                f"{adapter_class.__name__}.handled_events() must return at least one event"
