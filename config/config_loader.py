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
    Loader per configurazioni YAML con validazione.
    """
    
    @classmethod
    def load(cls, config_path: str, validate_adapters: bool = True) -> Dict[str, Any]:
        """
        Carica configurazione da file YAML.
        
        Args:
            config_path: Path al file YAML
            validate_adapters: Se True, valida che gli adapter configurati esistano
            
        Returns:
            Dict con configurazione completa
            
        Raises:
            FileNotFoundError: Se il file non esiste
            yaml.YAMLError: Se c'è un errore di parsing YAML
            ValueError: Se la configurazione non è valida
        """
        config_file = Path(config_path)
        
        # Se il file non esiste, solleva errore
        if not config_file.exists():
            error_msg = f"Configuration file not found: {config_path}"
            logger.error(f"❌ {error_msg}")
            raise FileNotFoundError(error_msg)
        
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            if config is None:
                raise ValueError("Configuration file is empty")
            
            # Valida struttura minima
            cls._validate_config_structure(config)
            
            # Valida adapter se richiesto
            if validate_adapters:
                cls._validate_adapters(config)
            
            logger.info(f"✅ Configuration loaded from: {config_path}")
            cls._log_config_summary(config)
            
            return config
            
        except yaml.YAMLError as e:
            error_msg = f"YAML parsing error in {config_path}: {e}"
            logger.error(f"❌ {error_msg}")
            raise yaml.YAMLError(error_msg)
        
        except Exception as e:
            logger.error(f"❌ Error loading config from {config_path}: {e}")
            raise
    
    @classmethod
    def _validate_config_structure(cls, config: Dict[str, Any]) -> None:
        """
        Valida che la configurazione abbia la struttura minima richiesta.
        
        Raises:
            ValueError: Se la configurazione non è valida
        """
        if 'brain' not in config:
            raise ValueError("Missing required 'brain' section in configuration")
        
        if 'adapters' not in config:
            raise ValueError("Missing required 'adapters' section in configuration")
        
        if 'input' not in config['adapters'] or 'output' not in config['adapters']:
            raise ValueError("Missing 'input' or 'output' in adapters configuration")
    
    @classmethod
    def _validate_adapters(cls, config: Dict[str, Any]) -> None:
        """
        Valida che gli adapter configurati esistano nel registry del factory.
        
        Raises:
            ValueError: Se un adapter configurato non esiste
        """
        # Import qui per evitare circular import
        from adapters.factory import AdapterFactory
        
        registered = AdapterFactory.get_registered_implementations()
        
        # Valida input adapters
        for adapter_name, adapter_config in config['adapters']['input'].items():
            implementation = adapter_config.get('implementation', '').lower()
            
            # Skip disabled adapters
            if implementation == 'disabled':
                continue
            
            if implementation not in registered['input']:
                available = ', '.join(registered['input'])
                raise ValueError(
                    f"Unknown input adapter implementation '{implementation}' "
                    f"for adapter '{adapter_name}'. "
                    f"Available: {available}"
                )
        
        # Valida output adapters
        for adapter_name, adapter_config in config['adapters']['output'].items():
            implementation = adapter_config.get('implementation', '').lower()
            
            # Skip disabled adapters
            if implementation == 'disabled':
                continue
            
            if implementation not in registered['output']:
                available = ', '.join(registered['output'])
                raise ValueError(
                    f"Unknown output adapter implementation '{implementation}' "
                    f"for adapter '{adapter_name}'. "
                    f"Available: {available}"
                )
    
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
            
        Raises:
            FileNotFoundError: Se il file non esiste
            json.JSONDecodeError: Se il file non è JSON valido
            ValueError: Se la configurazione è vuota o invalida
        """
        import json
        
        config_file = Path(json_path)
        
        if not config_file.exists():
            error_msg = f"Configuration file not found: {json_path}"
            logger.error(f"❌ {error_msg}")
            raise FileNotFoundError(error_msg)
        
        try:
            with open(config_file, 'r') as f:
                data = json.load(f)
            
            if not data:
                raise ValueError(f"Configuration file is empty: {json_path}")
            
            logger.info(f"✅ Loaded {json_path}")
            return data
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in {json_path}: {e}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"❌ Error loading {json_path}: {e}", exc_info=True)
            raise
