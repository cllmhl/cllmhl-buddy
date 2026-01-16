"""
Integration Tests - Full system flow
Test del flusso completo: Input → Brain → Router → Output
"""

import pytest
import time
import os
from queue import PriorityQueue
from unittest.mock import Mock, patch

from core import Event, EventType, EventPriority, create_input_event, create_output_event, EventRouter, BuddyBrain
from adapters.factory import AdapterFactory


class TestIntegration:
    """Test di integrazione end-to-end"""
    
    def test_event_priority_ordering(self):
        """Test che gli eventi siano processati per priorità"""
        pq = PriorityQueue()
        
        # Inserisci eventi in ordine casuale
        events = [
            create_input_event(EventType.USER_SPEECH, "low priority", "test", priority=EventPriority.LOW),
            create_input_event(EventType.USER_SPEECH, "critical!", "test", priority=EventPriority.CRITICAL),
            create_input_event(EventType.USER_SPEECH, "high priority", "test", priority=EventPriority.HIGH),
            create_input_event(EventType.USER_SPEECH, "normal", "test", priority=EventPriority.NORMAL),
        ]
        
        for e in events:
            pq.put(e)
        
        # Estrai in ordine di priorità
        first = pq.get()
        assert first.priority == EventPriority.CRITICAL
        assert first.content == "critical!"
        
        second = pq.get()
        assert second.priority == EventPriority.HIGH
        
        third = pq.get()
        assert third.priority == EventPriority.NORMAL
        
        fourth = pq.get()
        assert fourth.priority == EventPriority.LOW
    
    def test_brain_output_routing(self):
        """Test che il Brain produca eventi corretti"""
        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'fake_key'}):
            brain = BuddyBrain('test_brain', {
                'model_id': 'gemini-2.0-flash-exp',
                'temperature': 0.7
            })
        
        # Mock della risposta LLM
        with patch.object(brain, '_generate_response', return_value="Ciao!"):
            input_event = create_input_event(
                EventType.USER_SPEECH,
                "test",
                source="test"
            )
            
            output_events = brain.process_event(input_event)
            
            # Verifica che ci siano almeno SPEAK e SAVE_HISTORY
            assert len(output_events) >= 2
            
            event_types = [e.type for e in output_events]
            assert EventType.SPEAK in event_types
            assert EventType.SAVE_HISTORY in event_types
    
    def test_router_multi_destination(self):
        """Test che il Router invii a più destinazioni"""
        router = EventRouter()
        
        # Crea 3 code di output
        queue1 = PriorityQueue()
        queue2 = PriorityQueue()
        queue3 = PriorityQueue()
        
        # Registra tutte e tre per SPEAK
        router.register_route(EventType.SPEAK, queue1)
        router.register_route(EventType.SPEAK, queue2)
        router.register_route(EventType.SPEAK, queue3)
        
        # Crea evento
        event = Event(
            priority=EventPriority.NORMAL,
            type=EventType.SPEAK,
            content="test message",
            source="test"
        )
        
        # Invia
        router.route_event(event)
        
        # Verifica che sia arrivato a tutte e tre
        assert queue1.qsize() == 1
        assert queue2.qsize() == 1
        assert queue3.qsize() == 1
        
        # Verifica contenuto
        e1 = queue1.get()
        e2 = queue2.get()
        e3 = queue3.get()
        
        assert e1.content == "test message"
        assert e2.content == "test message"
        assert e3.content == "test message"
    
    def test_adapter_factory_creation(self):
        """Test che il Factory crei gli adapter corretti"""
        
        # Test output adapters
        mock_voice = AdapterFactory.create_output_adapter(
            'voice', {'implementation': 'log', 'config': {'log_file': '/tmp/test.log'}}
        )
        assert mock_voice is not None
        
        mock_led = AdapterFactory.create_output_adapter(
            'led', {'implementation': 'mock', 'config': {}}
        )
        assert mock_led is not None
    
    def test_voice_input_adapter_registered(self):
        """Test che Voice Input adapter sia registrato"""
        assert 'jabra' in AdapterFactory._input_implementations
        assert 'mock_voice' in AdapterFactory._input_implementations
        
        # Crea mock voice adapter
        mock_voice = AdapterFactory.create_input_adapter(
            'voice', {'implementation': 'mock_voice', 'config': {'interval': 5.0}}
        )
        assert mock_voice is not None
    
    def test_radar_adapter_registered(self):
        """Test che Radar adapter sia registrato"""
        assert 'radar' in AdapterFactory._input_implementations
        assert 'mock_radar' in AdapterFactory._input_implementations
        
        # Crea mock radar adapter
        mock_radar = AdapterFactory.create_input_adapter(
            'radar', {'implementation': 'mock_radar', 'config': {'interval': 1.0}}
        )
        assert mock_radar is not None
    
    def test_temperature_adapter_registered(self):
        """Test che Temperature adapter sia registrato"""
        assert 'temperature' in AdapterFactory._input_implementations
        assert 'mock_temperature' in AdapterFactory._input_implementations
        
        # Crea mock temperature adapter
        mock_temp = AdapterFactory.create_input_adapter(
            'temperature', {'implementation': 'mock_temperature', 'config': {'interval': 1.0}}
        )
        assert mock_temp is not None
    
    def test_audio_device_manager_coordination(self):
        """Test che AudioDeviceManager coordini input/output"""
        from adapters.audio_device_manager import get_jabra_manager, AudioDeviceState
        
        manager = get_jabra_manager()
        
        # Reset state
        manager.release()
        
        # Stato iniziale
        assert manager.state == AudioDeviceState.IDLE
        
        # Richiedi output
        success = manager.request_output()
        assert success
        assert manager.state == AudioDeviceState.SPEAKING
        
        # Non può fare input mentre parla
        can_listen = manager.request_input()
        assert not can_listen
        
        # Rilascia
        manager.release()
        assert manager.state == AudioDeviceState.IDLE
        
        # Ora può fare input
        can_listen = manager.request_input()
        assert can_listen
        assert manager.state == AudioDeviceState.LISTENING
        
        # Rilascia
        manager.release()
        assert manager.state == AudioDeviceState.IDLE


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
