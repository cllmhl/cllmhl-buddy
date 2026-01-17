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
    
    def test_register_input_implementation(self):
        """Test registrazione classe input"""
        AdapterFactory.register_input("DummyInputAdapter", DummyInputAdapter)
        
        classes = AdapterFactory.get_registered_classes()
        assert "DummyInputAdapter" in classes['input']
    
    def test_register_output_implementation(self):
        """Test registrazione classe output"""
        AdapterFactory.register_output("DummyOutputAdapter", DummyOutputAdapter)
        
        classes = AdapterFactory.get_registered_classes()
        assert "DummyOutputAdapter" in classes['output']
    
    def test_create_input_adapter_success(self):
        """Test creazione adapter input con successo"""
        AdapterFactory.register_input("DummyInputAdapter", DummyInputAdapter)
        
        test_queue = queue.PriorityQueue()
        config = {'test': 'value'}
        
        adapter = AdapterFactory.create_input_adapter("DummyInputAdapter", config, test_queue)
        
        assert adapter is not None
        assert isinstance(adapter, DummyInputAdapter)
        assert adapter.name == "DummyInputAdapter"
        assert adapter.input_queue == test_queue
    
    def test_create_input_adapter_unknown(self):
        """Test creazione adapter con classe sconosciuta"""
        test_queue = queue.PriorityQueue()
        
        adapter = AdapterFactory.create_input_adapter("NonexistentAdapter", {}, test_queue)
        
        assert adapter is None
    
    def test_create_output_adapter_success(self):
        """Test creazione adapter output con successo"""
        AdapterFactory.register_output("DummyOutputAdapter", DummyOutputAdapter)
        
        config = {}
        
        adapter = AdapterFactory.create_output_adapter("DummyOutputAdapter", config)
        
        assert adapter is not None
        assert isinstance(adapter, DummyOutputAdapter)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
