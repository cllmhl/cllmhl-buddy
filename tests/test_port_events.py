"""
Test che le Port dichiarino correttamente gli eventi gestiti/emessi
"""

import pytest
from adapters.ports import (
    VoiceOutputPort, LEDOutputPort, DatabaseOutputPort,
    VoiceInputPort, RadarInputPort, TemperatureInputPort
)
from core.events import EventType


class TestOutputPortEvents:
    """Test che le OutputPort dichiarino correttamente handled_events()"""
    
    def test_voice_output_port_declares_events(self):
        """VoiceOutputPort dichiara quali eventi gestisce"""
        events = VoiceOutputPort.handled_events()
        assert EventType.SPEAK in events
        assert len(events) == 1
    
    def test_led_output_port_declares_events(self):
        """LEDOutputPort dichiara quali eventi gestisce"""
        events = LEDOutputPort.handled_events()
        assert EventType.LED_CONTROL in events
        assert len(events) == 1
    
    def test_database_output_port_declares_events(self):
        """DatabaseOutputPort dichiara quali eventi gestisce"""
        events = DatabaseOutputPort.handled_events()
        assert EventType.SAVE_HISTORY in events
        assert EventType.SAVE_MEMORY in events
        assert len(events) == 2
    
    def test_event_routing_built_from_port_declarations(self):
        """Il routing può essere costruito dinamicamente dalle dichiarazioni delle Port"""
        # Crea adapter mock per testare
        from adapters.output.voice_output import MockVoiceOutput
        from adapters.output.led_output import MockLEDOutput
        from adapters.output.database_output import MockDatabaseOutput
        
        adapters = [
            MockVoiceOutput("test_voice", {}),
            MockLEDOutput("test_led", {}),
            MockDatabaseOutput("test_db", {})
        ]
        
        # Verifica che ogni adapter dichiari gli eventi corretti
        voice_events = MockVoiceOutput.handled_events()
        assert EventType.SPEAK in voice_events
        
        led_events = MockLEDOutput.handled_events()
        assert EventType.LED_CONTROL in led_events
        
        db_events = MockDatabaseOutput.handled_events()
        assert EventType.SAVE_HISTORY in db_events
        assert EventType.SAVE_MEMORY in db_events


class TestInputPortEvents:
    """Test che le InputPort dichiarino correttamente emitted_events()"""
    
    def test_voice_input_port_declares_events(self):
        """VoiceInputPort dichiara quali eventi emette"""
        events = VoiceInputPort.emitted_events()
        assert EventType.USER_SPEECH in events
        assert len(events) == 1
    
    def test_radar_input_port_declares_events(self):
        """RadarInputPort dichiara quali eventi emette"""
        events = RadarInputPort.emitted_events()
        assert EventType.SENSOR_PRESENCE in events
        assert EventType.SENSOR_MOVEMENT in events
        assert len(events) == 2
    
    def test_temperature_input_port_declares_events(self):
        """TemperatureInputPort dichiara quali eventi emette"""
        events = TemperatureInputPort.emitted_events()
        assert EventType.SENSOR_TEMPERATURE in events
        assert EventType.SENSOR_HUMIDITY in events
        assert len(events) == 2
    
    def test_input_events_are_distinct(self):
        """Eventi emessi da diverse InputPort non si sovrappongono"""
        voice_events = set(VoiceInputPort.emitted_events())
        radar_events = set(RadarInputPort.emitted_events())
        temp_events = set(TemperatureInputPort.emitted_events())
        
        # Voice non si sovrappone con sensori
        assert not voice_events.intersection(radar_events)
        assert not voice_events.intersection(temp_events)
        
        # Radar e Temperature non si sovrappongono
        assert not radar_events.intersection(temp_events)


class TestPortSignatures:
    """Test che le Port abbiano signature chiare e complete"""
    
    def test_all_output_ports_implement_handled_events(self):
        """Tutte le OutputPort specializzate implementano handled_events()"""
        output_ports = [VoiceOutputPort, LEDOutputPort, DatabaseOutputPort]
        
        for port_class in output_ports:
            assert hasattr(port_class, 'handled_events'), \
                f"{port_class.__name__} must implement handled_events()"
            
            events = port_class.handled_events()
            assert len(events) > 0, \
                f"{port_class.__name__}.handled_events() must return at least one event"
    
    def test_all_input_ports_implement_emitted_events(self):
        """Tutte le InputPort specializzate implementano emitted_events()"""
        input_ports = [VoiceInputPort, RadarInputPort, TemperatureInputPort]
        
        for port_class in input_ports:
            assert hasattr(port_class, 'emitted_events'), \
                f"{port_class.__name__} must implement emitted_events()"
            
            events = port_class.emitted_events()
            assert len(events) > 0, \
                f"{port_class.__name__}.emitted_events() must return at least one event"
