"""
Configuration Loader - Carica e valida configurazioni YAML
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigLoader:
    """
    Loader per configurazioni YAML con validazione e defaults.
    """
    
    DEFAULT_CONFIG = {
        'brain': {
            'model_id': 'gemini-2.0-flash-exp',
            'temperature': 0.7,
            'system_instruction': 'Sei Buddy, un assistente AI amichevole.'
        },
        'adapters': {
            'input': {},
            'output': {}
        },
        'queues': {
            'input_maxsize': 100,
            'voice_maxsize': 50,
            'led_maxsize': 100,
            'database_maxsize': 500,
            'log_maxsize': 1000
        }
    }
    
    @classmethod
    def load(cls, config_path: str) -> Dict[str, Any]:
        """
        Carica configurazione da file YAML.
        
        Args:
            config_path: Path al file YAML
            
        Returns:
            Dict con configurazione completa
        """
        config_file = Path(config_path)
        
        # Se il file non esiste, usa defaults
        if not config_file.exists():
            logger.warning(f"⚠️  Config file not found: {config_path}")
            logger.info("Using default configuration")
            return cls.DEFAULT_CONFIG.copy()
        
        try:
            with open(config_file, 'r') as f:
                loaded_config = yaml.safe_load(f)
            
            # Merge con defaults
            config = cls._merge_with_defaults(loaded_config)
            
            logger.info(f"✅ Configuration loaded from: {config_path}")
            cls._log_config_summary(config)
            
            return config
            
        except yaml.YAMLError as e:
            logger.error(f"❌ YAML parsing error: {e}")
            logger.info("Using default configuration")
            return cls.DEFAULT_CONFIG.copy()
        
        except Exception as e:
            logger.error(f"❌ Error loading config: {e}")
            logger.info("Using default configuration")
            return cls.DEFAULT_CONFIG.copy()
    
    @classmethod
    def _merge_with_defaults(cls, loaded: Dict[str, Any]) -> Dict[str, Any]:
        """Merge configurazione caricata con defaults"""
        import copy
        config = copy.deepcopy(cls.DEFAULT_CONFIG)
        
        # Merge brain config
        if 'brain' in loaded:
            config['brain'].update(loaded['brain'])
        
        # Merge adapters
        if 'adapters' in loaded:
            if 'input' in loaded['adapters']:
                config['adapters']['input'] = loaded['adapters']['input']
            if 'output' in loaded['adapters']:
                config['adapters']['output'] = loaded['adapters']['output']
        
        # Merge queues
        if 'queues' in loaded:
            config['queues'].update(loaded['queues'])
        
        return config
    
    @classmethod
    def _log_config_summary(cls, config: Dict[str, Any]) -> None:
        """Log riassunto configurazione"""
        logger.info("📋 Configuration Summary:")
        logger.info(f"  Brain Model: {config['brain']['model_id']}")
        logger.info(f"  Input Adapters: {len(config['adapters']['input'])}")
        logger.info(f"  Output Adapters: {len(config['adapters']['output'])}")
    
    @classmethod
    def load_buddy_config_json(cls, json_path: str = "buddy_config.json") -> Dict[str, Any]:
        """
        Carica il vecchio buddy_config.json per compatibilità.
        
        Args:
            json_path: Path al file JSON
            
        Returns:
            Dict con configurazione brain
        """
        import json
        
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            logger.info(f"✅ Loaded buddy_config.json")
            return data
            
        except FileNotFoundError:
            logger.warning(f"⚠️  {json_path} not found")
            return {}
        except Exception as e:
            logger.error(f"❌ Error loading {json_path}: {e}")
            return {}
