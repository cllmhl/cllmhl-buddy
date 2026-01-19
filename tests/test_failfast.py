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
        """Adapter ritornano EventType reali, non liste vuote"""
        from adapters.output.voice_output import JabraVoiceOutput
        from adapters.output.led_output import GPIOLEDOutput
        from adapters.output.database_output import DatabaseOutput
        from core.events import OutputEventType
        
        # Output adapters - ritornano OutputEventType
        voice_events = JabraVoiceOutput.handled_events()
        assert len(voice_events) > 0
        assert all(isinstance(e, OutputEventType) for e in voice_events)
        
        led_events = GPIOLEDOutput.handled_events()
        assert len(led_events) > 0
        assert all(isinstance(e, OutputEventType) for e in led_events)
        
        db_events = DatabaseOutput.handled_events()
        assert len(db_events) > 0
        assert all(isinstance(e, OutputEventType) for e in db_events)
    
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
        from adapters.output.voice_output import JabraVoiceOutput
        import inspect
        
        # Ottieni il source del metodo
        source = inspect.getsource(JabraVoiceOutput.handled_events)
        
        # Non deve contenere try/except
        assert 'try:' not in source.lower()
        assert 'except' not in source.lower()
    
    def test_no_try_except_in_emitted_events(self):
        """Input adapter non usano metodo emitted_events - test rimosso"""
        # Gli input adapter non hanno il metodo emitted_events,
        # quindi questo test non è più applicabile
        pass
