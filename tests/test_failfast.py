"""
Test che il sistema fallisca immediatamente (fail-fast) in caso di problemi.
Nessun fallback silenzioso che maschera errori.
"""

import pytest


class TestFailFast:
    """Test comportamento fail-fast del sistema"""
    
    def test_ports_require_core_events(self):
        """Port falliscono immediatamente se core.events non è disponibile"""
        import sys
        
        # Backup modulo
        core_events = sys.modules.get('core.events')
        
        try:
            # Simula modulo mancante
            if 'core.events' in sys.modules:
                del sys.modules['core.events']
            sys.modules['core.events'] = None
            
            # Deve fallire immediatamente
            with pytest.raises((ImportError, ModuleNotFoundError, AttributeError)):
                # Force reimport
                if 'adapters.ports' in sys.modules:
                    del sys.modules['adapters.ports']
                from adapters.ports import VoiceOutputPort
        
        finally:
            # Ripristina
            if core_events is not None:
                sys.modules['core.events'] = core_events
            elif 'core.events' in sys.modules:
                del sys.modules['core.events']
            
            # Reimport pulito
            if 'adapters.ports' in sys.modules:
                del sys.modules['adapters.ports']
    
    def test_ports_return_event_types_not_empty_list(self):
        """Port ritornano EventType reali, non liste vuote"""
        from adapters.ports import (
            VoiceOutputPort, LEDOutputPort, DatabaseOutputPort,
            VoiceInputPort, RadarInputPort, TemperatureInputPort
        )
        from core.events import EventType
        
        # Output ports
        voice_events = VoiceOutputPort.handled_events()
        assert len(voice_events) > 0
        assert all(isinstance(e, EventType) for e in voice_events)
        
        led_events = LEDOutputPort.handled_events()
        assert len(led_events) > 0
        assert all(isinstance(e, EventType) for e in led_events)
        
        db_events = DatabaseOutputPort.handled_events()
        assert len(db_events) > 0
        assert all(isinstance(e, EventType) for e in db_events)
        
        # Input ports
        voice_input_events = VoiceInputPort.emitted_events()
        assert len(voice_input_events) > 0
        assert all(isinstance(e, EventType) for e in voice_input_events)
        
        radar_events = RadarInputPort.emitted_events()
        assert len(radar_events) > 0
        assert all(isinstance(e, EventType) for e in radar_events)
        
        temp_events = TemperatureInputPort.emitted_events()
        assert len(temp_events) > 0
        assert all(isinstance(e, EventType) for e in temp_events)
    
    def test_build_event_routing_fails_without_adapters(self):
        """build_event_routing_from_ports fallisce se adapters non disponibili"""
        import sys
        
        # Backup
        voice_output = sys.modules.get('adapters.output.voice_output')
        
        try:
            # Simula modulo mancante
            if 'adapters.output.voice_output' in sys.modules:
                del sys.modules['adapters.output.voice_output']
            sys.modules['adapters.output.voice_output'] = None
            
            # Deve fallire immediatamente, non ritornare dict vuoto
            with pytest.raises((ImportError, ModuleNotFoundError, AttributeError)):
                # Force reimport
                if 'core.events' in sys.modules:
                    del sys.modules['core.events']
                from core.events import build_event_routing_from_ports
                build_event_routing_from_ports()
        
        finally:
            # Ripristina
            if voice_output is not None:
                sys.modules['adapters.output.voice_output'] = voice_output
            elif 'adapters.output.voice_output' in sys.modules:
                del sys.modules['adapters.output.voice_output']
            
            # Reimport pulito
            if 'core.events' in sys.modules:
                del sys.modules['core.events']


class TestNoSilentFallbacks:
    """Verifica che non ci siano fallback silenziosi che mascherano errori"""
    
    def test_no_try_except_in_handled_events(self):
        """handled_events() non ha try/except che maschera errori"""
        from adapters.ports import VoiceOutputPort
        import inspect
        
        # Ottieni il source del metodo
        source = inspect.getsource(VoiceOutputPort.handled_events)
        
        # Non deve contenere try/except
        assert 'try:' not in source.lower()
        assert 'except' not in source.lower()
    
    def test_no_try_except_in_emitted_events(self):
        """emitted_events() non ha try/except che maschera errori"""
        from adapters.ports import VoiceInputPort
        import inspect
        
        # Ottieni il source del metodo
        source = inspect.getsource(VoiceInputPort.emitted_events)
        
        # Non deve contenere try/except
        assert 'try:' not in source.lower()
        assert 'except' not in source.lower()
