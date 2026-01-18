"""
Integration Tests - Full system flow
Test del flusso completo: Input → Brain → Router → Output
"""

import pytest
import time
import os
from queue import PriorityQueue
from unittest.mock import Mock, patch

from core import Event, InputEventType, OutputEventType, EventPriority, create_input_event, create_output_event, EventRouter, BuddyBrain
from adapters.factory import AdapterFactory


class TestIntegration:
    """Test di integrazione end-to-end"""
    
    def test_event_priority_ordering(self):
        """Test che gli eventi siano processati per priorità"""
        pq = PriorityQueue()
        
        # Inserisci eventi in ordine casuale
        events = [
            create_input_event(InputEventType.USER_SPEECH, "low priority", "test", priority=EventPriority.LOW),
            create_input_event(InputEventType.USER_SPEECH, "critical!", "test", priority=EventPriority.CRITICAL),
            create_input_event(InputEventType.USER_SPEECH, "high priority", "test", priority=EventPriority.HIGH),
            create_input_event(InputEventType.USER_SPEECH, "normal", "test", priority=EventPriority.NORMAL),
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
                'temperature': 0.7,
                'system_instruction': 'Test',
                'archivist_interval': 300.0
            })
        
        # Mock della risposta LLM
        with patch.object(brain, '_generate_response', return_value="Ciao!"):
            input_event = create_input_event(
                InputEventType.USER_SPEECH,
                "test",
                source="test"
            )
            
            output_events = brain.process_event(input_event)
            
            # Verifica che ci siano almeno SPEAK e SAVE_HISTORY
            assert len(output_events) >= 2
            
            event_types = [e.type for e in output_events]
            assert OutputEventType.SPEAK in event_types
            assert OutputEventType.SAVE_HISTORY in event_types
    
    def test_router_multi_destination(self):
        """Test che il Router invii a più destinazioni"""
        router = EventRouter()
        
        # Crea 3 mock adapter
        adapter1 = Mock()
        adapter1.name = "adapter1"
        adapter1.events_received = []
        adapter1.send_event = lambda e: adapter1.events_received.append(e) or True
        
        adapter2 = Mock()
        adapter2.name = "adapter2"
        adapter2.events_received = []
        adapter2.send_event = lambda e: adapter2.events_received.append(e) or True
        
        adapter3 = Mock()
        adapter3.name = "adapter3"
        adapter3.events_received = []
        adapter3.send_event = lambda e: adapter3.events_received.append(e) or True
        
        # Registra tutti e tre per SPEAK
        router.register_route(OutputEventType.SPEAK, adapter1)
        router.register_route(OutputEventType.SPEAK, adapter2)
        router.register_route(OutputEventType.SPEAK, adapter3)
        
        # Crea evento SPEAK
        event = Event(
            priority=EventPriority.NORMAL,
            type=OutputEventType.SPEAK,
            content="test message",
            source="test"
        )
        
        # Invia
        router.route_event(event)
        
        # Verifica che sia arrivato a tutti e tre
        assert len(adapter1.events_received) == 1
        assert len(adapter2.events_received) == 1
        assert len(adapter3.events_received) == 1
        
        # Verifica contenuto
        assert adapter1.events_received[0].content == "test message"
        assert adapter2.events_received[0].content == "test message"
        assert adapter3.events_received[0].content == "test message"
    
    def test_adapter_factory_creation(self):
        """Test che il Factory crei gli adapter corretti"""
        
        # Test output adapters
        mock_voice = AdapterFactory.create_output_adapter(
            "MockVoiceOutput", {}
        )
        assert mock_voice is not None
        
        mock_led = AdapterFactory.create_output_adapter(
            "MockLEDOutput", {}
        )
        assert mock_led is not None
    
    def test_voice_input_adapter_available(self):
        """Test che Voice Input adapter sia disponibile"""
        available = AdapterFactory.get_available_classes()
        assert "JabraVoiceInput" in available['input']
        assert "MockVoiceInput" in available['input']
        
        # Crea mock ear adapter
        input_queue = PriorityQueue()
        mock_ear = AdapterFactory.create_input_adapter(
            "MockVoiceInput", {'interval': 5.0}, input_queue
        )
        assert mock_ear is not None
    
    def test_radar_adapter_available(self):
        """Test che Radar adapter sia disponibile"""
        available = AdapterFactory.get_available_classes()
        assert "RadarInput" in available['input']
        assert "MockRadarInput" in available['input']
        
        # Crea mock radar adapter
        input_queue = PriorityQueue()
        mock_radar = AdapterFactory.create_input_adapter(
            "MockRadarInput", {'interval': 1.0}, input_queue
        )
        assert mock_radar is not None
    
    def test_temperature_adapter_available(self):
        """Test che Temperature adapter sia disponibile"""
        available = AdapterFactory.get_available_classes()
        assert "TemperatureInput" in available['input']
        assert "MockTemperatureInput" in available['input']
        
        # Crea mock temperature adapter
        input_queue = PriorityQueue()
        mock_temp = AdapterFactory.create_input_adapter(
            "MockTemperatureInput", {'interval': 1.0}, input_queue
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
