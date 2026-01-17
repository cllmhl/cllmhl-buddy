"""
Tests per il Core - Events, Router, Brain
"""

import pytest
import queue
import time
from unittest.mock import Mock, patch

from core import (
    Event, EventType, EventPriority,
    create_input_event, create_output_event,
    EventRouter, BuddyBrain
)


# Mock adapter per testing router
class MockOutputAdapter:
    """Mock adapter per testing EventRouter"""
    def __init__(self, name):
        self.name = name
        self.events_received = []
    
    def send_event(self, event):
        """Simula send_event() dell'adapter"""
        self.events_received.append(event)
        return True


class TestEvents:
    """Test per il sistema di eventi"""
    
    def test_event_creation(self):
        """Test creazione evento base"""
        event = Event(
            priority=EventPriority.NORMAL,
            type=EventType.USER_SPEECH,
            content="Ciao Buddy"
        )
        
        assert event.type == EventType.USER_SPEECH
        assert event.priority == EventPriority.NORMAL
        assert event.content == "Ciao Buddy"
        assert event.timestamp > 0
    
    def test_event_priority_ordering(self):
        """Test che eventi con priorità più alta vengano prima"""
        critical = Event(EventPriority.CRITICAL, EventType.SHUTDOWN, "stop")
        normal = Event(EventPriority.NORMAL, EventType.USER_SPEECH, "ciao")
        low = Event(EventPriority.LOW, EventType.SPEAK, "speak")
        
        # In una PriorityQueue, il minore viene prima
        assert critical < normal
        assert normal < low
        assert critical < low
    
    def test_priority_queue_ordering(self):
        """Test che PriorityQueue ordini correttamente gli eventi"""
        q = queue.PriorityQueue()
        
        # Inserisci in ordine casuale
        q.put(Event(EventPriority.LOW, EventType.SPEAK, "low"))
        q.put(Event(EventPriority.CRITICAL, EventType.SHUTDOWN, "critical"))
        q.put(Event(EventPriority.NORMAL, EventType.USER_SPEECH, "normal"))
        
        # Estrai: dovrebbero uscire per priorità
        first = q.get()
        second = q.get()
        third = q.get()
        
        assert first.priority == EventPriority.CRITICAL
        assert second.priority == EventPriority.NORMAL
        assert third.priority == EventPriority.LOW
    
    def test_create_input_event_helper(self):
        """Test helper per creare eventi di input"""
        event = create_input_event(
            EventType.USER_SPEECH,
            "test message",
            source="voice",
            priority=EventPriority.HIGH
        )
        
        assert event.type == EventType.USER_SPEECH
        assert event.content == "test message"
        assert event.source == "voice"
        assert event.priority == EventPriority.HIGH
    
    def test_create_output_event_helper(self):
        """Test helper per creare eventi di output"""
        event = create_output_event(
            EventType.SPEAK,
            "Hello world",
            priority=EventPriority.HIGH,
            metadata={"triggered_by": "user"}
        )
        
        assert event.type == EventType.SPEAK
        assert event.content == "Hello world"
        assert event.priority == EventPriority.HIGH
        assert event.metadata["triggered_by"] == "user"


class TestEventRouter:
    """Test per l'EventRouter"""
    
    def test_router_initialization(self):
        """Test inizializzazione router"""
        router = EventRouter()
        
        stats = router.get_stats()
        assert stats['routed'] == 0
        assert stats['dropped'] == 0
        assert stats['routes_count'] == 0
    
    def test_register_route(self):
        """Test registrazione route"""
        router = EventRouter()
        mock_adapter = MockOutputAdapter("test_adapter")
        
        router.register_route(EventType.SPEAK, mock_adapter, "test_adapter")
        
        routes = router.get_routes()
        assert EventType.SPEAK in routes
        assert routes[EventType.SPEAK] == 1
    
    def test_route_event_success(self):
        """Test routing evento con successo"""
        router = EventRouter()
        mock_adapter = MockOutputAdapter("voice")
        
        router.register_route(EventType.SPEAK, mock_adapter, "voice")
        
        event = create_output_event(EventType.SPEAK, "test")
        routed = router.route_event(event)
        
        assert routed == 1
        assert len(mock_adapter.events_received) == 1
        assert mock_adapter.events_received[0].content == "test"
    
    def test_route_event_no_route(self):
        """Test routing evento senza route registrate"""
        router = EventRouter()
        
        event = create_output_event(EventType.SPEAK, "test")
        routed = router.route_event(event)
        
        assert routed == 0
        stats = router.get_stats()
        assert stats['no_route'] == 1
    
    def test_route_multiple_destinations(self):
        """Test broadcast a multiple destinazioni"""
        router = EventRouter()
        adapter1 = MockOutputAdapter("db1")
        adapter2 = MockOutputAdapter("db2")
        
        # Registra due destinazioni per lo stesso evento
        router.register_route(EventType.SAVE_HISTORY, adapter1, "db1")
        router.register_route(EventType.SAVE_HISTORY, adapter2, "db2")
        
        event = create_output_event(EventType.SAVE_HISTORY, "save data")
        routed = router.route_event(event)
        
        assert routed == 2
        assert len(adapter1.events_received) == 1
        assert len(adapter2.events_received) == 1
    
    def test_route_events_batch(self):
        """Test routing batch di eventi"""
        router = EventRouter()
        mock_adapter = MockOutputAdapter("voice_db")
        
        router.register_route(EventType.SPEAK, mock_adapter, "voice")
        router.register_route(EventType.SAVE_HISTORY, mock_adapter, "db")
        
        events = [
            create_output_event(EventType.SPEAK, "speak1"),
            create_output_event(EventType.SAVE_HISTORY, "save1"),
            create_output_event(EventType.SPEAK, "speak2")
        ]
        
        total_routed = router.route_events(events)
        assert total_routed == 3


class TestBuddyBrain:
    """Test per BuddyBrain (con mock LLM)"""
    
    @pytest.fixture
    def mock_brain_config(self):
        """Config di test per brain"""
        return {
            'model_id': 'test-model',
            'temperature': 0.7,
            'system_instruction': 'Test instruction'
        }
    
    @patch('core.brain.genai.Client')
    def test_brain_initialization(self, mock_client, mock_brain_config):
        """Test inizializzazione brain"""
        brain = BuddyBrain("fake_api_key", mock_brain_config)
        
        assert brain.model_id == 'test-model'
        assert brain.config == mock_brain_config
    
    @patch('core.brain.genai.Client')
    def test_brain_process_user_speech(self, mock_client, mock_brain_config):
        """Test processing di input vocale"""
        # Mock LLM response
        mock_session = Mock()
        mock_response = Mock()
        mock_response.text = "Ciao! Come posso aiutarti?"
        mock_response.candidates = [Mock(grounding_metadata=None)]
        mock_session.send_message.return_value = mock_response
        
        mock_client_instance = Mock()
        mock_client_instance.chats.create.return_value = mock_session
        mock_client.return_value = mock_client_instance
        
        brain = BuddyBrain("fake_api_key", mock_brain_config)
        
        # Crea evento input
        input_event = create_input_event(
            EventType.USER_SPEECH,
            "Ciao",
            source="voice"
        )
        
        # Processa
        output_events = brain.process_event(input_event)
        
        # Verifica che ci siano eventi di output
        assert len(output_events) > 0
        
        # Verifica che ci sia un evento SPEAK
        speak_events = [e for e in output_events if e.type == EventType.SPEAK]
        assert len(speak_events) == 1
        assert "Ciao" in speak_events[0].content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
