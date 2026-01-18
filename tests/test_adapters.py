"""
Tests per Adapters - Ports e Factory
"""

import pytest
import queue
from unittest.mock import Mock

from adapters import InputPort, OutputPort, AdapterFactory


class DummyInputAdapter(InputPort):
    """Adapter di test per input"""
    
    def start(self):
        self.running = True
    
    def stop(self):
        self.running = False


class DummyOutputAdapter(OutputPort):
    """Adapter di test per output"""
    
    def handled_events(self):
        return ["test_event"]
    
    def start(self):
        self.running = True
    
    def stop(self):
        self.running = False


class TestPorts:
    """Test per le interfacce Port"""
    
    def test_input_port_initialization(self):
        """Test inizializzazione InputPort"""
        test_queue = queue.PriorityQueue()
        adapter = DummyInputAdapter("test", {}, test_queue)
        
        assert adapter.name == "test"
        assert adapter.running is False
        assert adapter.input_queue == test_queue
    
    def test_input_port_start(self):
        """Test start di InputPort"""
        test_queue = queue.PriorityQueue()
        adapter = DummyInputAdapter("test", {}, test_queue)
        
        adapter.start()
        
        assert adapter.running is True
        assert adapter.input_queue == test_queue
    
    def test_output_port_initialization(self):
        """Test inizializzazione OutputPort"""
        adapter = DummyOutputAdapter("test", {})
        
        assert adapter.name == "test"
        assert adapter.running is False
        assert adapter.output_queue is not None  # Ora ha una coda interna
        assert adapter.output_queue.empty()
    
    def test_output_port_start(self):
        """Test start di OutputPort"""
        adapter = DummyOutputAdapter("test", {})
        
        adapter.start()  # Non riceve più la coda esterna
        
        assert adapter.running is True
        assert adapter.output_queue is not None  # Ha la sua coda interna


class TestAdapterFactory:
    """Test per AdapterFactory"""
    
    def test_get_available_classes(self):
        """Test recupero classi disponibili dai moduli"""
        classes = AdapterFactory.get_available_classes()
        
        # Verifica che siano presenti le classi principali
        assert 'MockVoiceInput' in classes['input']
        assert 'MockVoiceOutput' in classes['output']
        assert 'PipeInputAdapter' in classes['input']
    
    def test_create_input_adapter_success(self):
        """Test creazione adapter input con successo"""
        test_queue = queue.PriorityQueue()
        config = {'test': 'value'}
        
        # Usa un adapter reale esistente
        adapter = AdapterFactory.create_input_adapter("MockVoiceInput", config, test_queue)
        
        assert adapter is not None
        assert adapter.name == "MockVoiceInput"
        assert adapter.input_queue == test_queue
    
    def test_create_input_adapter_unknown(self):
        """Test creazione adapter con classe sconosciuta solleva ValueError"""
        test_queue = queue.PriorityQueue()
        
        with pytest.raises(ValueError, match="Unknown input adapter class 'NonexistentAdapter'"):
            AdapterFactory.create_input_adapter("NonexistentAdapter", {}, test_queue)
    
    def test_create_output_adapter_success(self):
        """Test creazione adapter output con successo"""
        config = {}
        
        # Usa un adapter reale esistente
        adapter = AdapterFactory.create_output_adapter("MockVoiceOutput", config)
        
        assert adapter is not None
        assert adapter.name == "MockVoiceOutput"
    
    def test_create_output_adapter_unknown(self):
        """Test creazione output adapter con classe sconosciuta solleva ValueError"""
        
        with pytest.raises(ValueError, match="Unknown output adapter class 'NonexistentAdapter'"):
            AdapterFactory.create_output_adapter("NonexistentAdapter", {})


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
