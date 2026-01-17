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
        """Test caricamento file inesistente solleva FileNotFoundError"""
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            ConfigLoader.load("nonexistent.yaml")
    
    def test_load_valid_yaml(self):
        """Test caricamento file YAML valido"""
        test_config = {
            'brain': {
                'model_id': 'test-model',
                'temperature': 0.5
            },
            'adapters': {
                'input': [
                    {
                        'class': 'JabraVoiceInput',
                        'config': {}
                    }
                ],
                'output': []
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
            assert len(config['adapters']['input']) == 1
        finally:
            Path(temp_path).unlink()
    
    def test_validate_config_missing_brain(self):
        """Test validazione configurazione senza brain"""
        invalid_config = {
            'adapters': {
                'input': [],
                'output': []
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(invalid_config, f)
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError, match="Missing required 'brain' section"):
                ConfigLoader.load(temp_path)
        finally:
            Path(temp_path).unlink()
    
    def test_invalid_yaml(self):
        """Test gestione YAML malformato solleva YAMLError"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name
        
        try:
            with pytest.raises(yaml.YAMLError, match="YAML parsing error"):
                ConfigLoader.load(temp_path)
        finally:
            Path(temp_path).unlink()
    
    def test_validate_unknown_input_adapter(self):
        """Test validazione adapter input sconosciuto"""
        invalid_config = {
            'brain': {
                'model_id': 'test-model',
                'temperature': 0.5
            },
            'adapters': {
                'input': [
                    {
                        'class': 'UnknownAdapter',
                        'config': {}
                    }
                ],
                'output': []
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(invalid_config, f)
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError, match="Unknown input adapter class 'UnknownAdapter'"):
                ConfigLoader.load(temp_path)
        finally:
            Path(temp_path).unlink()
    
    def test_validate_unknown_output_adapter(self):
        """Test validazione adapter output sconosciuto"""
        invalid_config = {
            'brain': {
                'model_id': 'test-model',
                'temperature': 0.5
            },
            'adapters': {
                'input': [],
                'output': [
                    {
                        'class': 'NonexistentAdapter',
                        'config': {}
                    }
                ]
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(invalid_config, f)
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError, match="Unknown output adapter class 'NonexistentAdapter'"):
                ConfigLoader.load(temp_path)
        finally:
            Path(temp_path).unlink()
    
    def test_validate_empty_adapters_ok(self):
        """Test che liste di adapter vuote non sollevino errore"""
        valid_config = {
            'brain': {
                'model_id': 'test-model',
                'temperature': 0.5
            },
            'adapters': {
                'input': [],
                'output': []
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(valid_config, f)
            temp_path = f.name
        
        try:
            # Non deve sollevare errore
            config = ConfigLoader.load(temp_path)
            assert config is not None
        finally:
            Path(temp_path).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
