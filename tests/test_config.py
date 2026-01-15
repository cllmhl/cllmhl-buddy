"""
Tests per ConfigLoader
"""

import pytest
import tempfile
import yaml
from pathlib import Path

from config.config_loader import ConfigLoader


class TestConfigLoader:
    """Test per il ConfigLoader"""
    
    def test_load_nonexistent_file(self):
        """Test caricamento file inesistente usa defaults"""
        config = ConfigLoader.load("nonexistent.yaml")
        
        assert 'brain' in config
        assert 'adapters' in config
        assert config['brain']['model_id'] == 'gemini-2.0-flash-exp'
    
    def test_load_valid_yaml(self):
        """Test caricamento file YAML valido"""
        test_config = {
            'brain': {
                'model_id': 'test-model',
                'temperature': 0.5
            },
            'adapters': {
                'input': {
                    'voice': {
                        'implementation': 'jabra'
                    }
                },
                'output': {}
            }
        }
        
        # Crea file temporaneo
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_config, f)
            temp_path = f.name
        
        try:
            config = ConfigLoader.load(temp_path)
            
            assert config['brain']['model_id'] == 'test-model'
            assert config['brain']['temperature'] == 0.5
            assert 'voice' in config['adapters']['input']
        finally:
            Path(temp_path).unlink()
    
    def test_merge_with_defaults(self):
        """Test merge con defaults"""
        partial_config = {
            'brain': {
                'model_id': 'custom-model'
            }
        }
        
        merged = ConfigLoader._merge_with_defaults(partial_config)
        
        # Deve avere il valore custom
        assert merged['brain']['model_id'] == 'custom-model'
        # Ma anche i defaults
        assert 'temperature' in merged['brain']
        assert 'adapters' in merged
    
    def test_invalid_yaml(self):
        """Test gestione YAML malformato"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name
        
        try:
            config = ConfigLoader.load(temp_path)
            
            # Deve fallback ai defaults
            assert config == ConfigLoader.DEFAULT_CONFIG
        finally:
            Path(temp_path).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
