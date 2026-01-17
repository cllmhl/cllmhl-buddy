"""
Tests per Adapters - Ports e Factory
"""

import pytest
import queue
from unittest.mock import Mock

from adapters import InputPort, OutputPort, AdapterFactory


class DummyInputAdapter(InputPort):
    """Adapter di test per input"""
    
    def start(self, input_queue):
        self.input_queue = input_queue
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
        adapter = DummyInputAdapter("test", {})
        
        assert adapter.name == "test"
        assert adapter.running is False
        assert adapter.input_queue is None
    
    def test_input_port_start(self):
        """Test start di InputPort"""
        adapter = DummyInputAdapter("test", {})
        test_queue = queue.PriorityQueue()
        
        adapter.start(test_queue)
        
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
        """Test registrazione implementazione input"""
        AdapterFactory.register_input("dummy", DummyInputAdapter)
        
        implementations = AdapterFactory.get_registered_implementations()
        assert "dummy" in implementations['input']
    
    def test_register_output_implementation(self):
        """Test registrazione implementazione output"""
        AdapterFactory.register_output("dummy", DummyOutputAdapter)
        
        implementations = AdapterFactory.get_registered_implementations()
        assert "dummy" in implementations['output']
    
    def test_create_input_adapter_success(self):
        """Test creazione adapter input con successo"""
        AdapterFactory.register_input("dummy", DummyInputAdapter)
        
        config = {
            'implementation': 'dummy',
            'config': {'test': 'value'}
        }
        
        adapter = AdapterFactory.create_input_adapter("test_type", config)
        
        assert adapter is not None
        assert isinstance(adapter, DummyInputAdapter)
        assert adapter.name == "test_type_dummy"
    
    def test_create_input_adapter_disabled(self):
        """Test creazione adapter disabilitato"""
        config = {
            'implementation': 'disabled',
            'config': {}
        }
        
        adapter = AdapterFactory.create_input_adapter("test", config)
        
        assert adapter is None
    
    def test_create_input_adapter_unknown(self):
        """Test creazione adapter con implementazione sconosciuta"""
        config = {
            'implementation': 'nonexistent',
            'config': {}
        }
        
        adapter = AdapterFactory.create_input_adapter("test", config)
        
        assert adapter is None
    
    def test_create_output_adapter_success(self):
        """Test creazione adapter output con successo"""
        AdapterFactory.register_output("dummy", DummyOutputAdapter)
        
        config = {
            'implementation': 'dummy',
            'config': {}
        }
        
        adapter = AdapterFactory.create_output_adapter("test_type", config)
        
        assert adapter is not None
        assert isinstance(adapter, DummyOutputAdapter)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
