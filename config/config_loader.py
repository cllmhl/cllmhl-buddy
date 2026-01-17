"""
Configuration Loader - Carica e valida configurazioni YAML
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


def get_buddy_home() -> Path:
    """
    Ottiene la directory home di Buddy.
    
    Usa in ordine:
    1. BUDDY_HOME environment variable (se impostata)
    2. Directory del file che importa questo modulo
    3. Current working directory (fallback)
    
    Returns:
        Path assoluto alla directory home di Buddy
    """
    # 1. Prova con variabile d'ambiente
    if 'BUDDY_HOME' in os.environ:
        buddy_home = Path(os.environ['BUDDY_HOME']).resolve()
        logger.debug(f"BUDDY_HOME from env: {buddy_home}")
        return buddy_home
    
    # 2. Usa directory di questo file (config/) e risali alla root
    config_dir = Path(__file__).parent.resolve()
    buddy_home = config_dir.parent
    logger.debug(f"BUDDY_HOME auto-detected: {buddy_home}")
    return buddy_home


def resolve_path(path: str, relative_to: Optional[Path] = None) -> Path:
    """
    Risolve un path in assoluto.
    
    Se il path è già assoluto, lo restituisce così com'è.
    Se è relativo, lo risolve rispetto a BUDDY_HOME o alla directory specificata.
    
    Args:
        path: Path da risolvere (può essere relativo o assoluto)
        relative_to: Directory base per path relativi (default: BUDDY_HOME)
        
    Returns:
        Path assoluto
    """
    p = Path(path)
    
    # Se è già assoluto, restituiscilo
    if p.is_absolute():
        return p.resolve()
    
    # Se è relativo, risolvilo rispetto a BUDDY_HOME
    base_dir = relative_to if relative_to else get_buddy_home()
    return (base_dir / p).resolve()


class ConfigLoader:
    """
    Loader per configurazioni YAML con validazione.
    """
    
    @classmethod
    def load(cls, config_path: str, validate_adapters: bool = True) -> Dict[str, Any]:
        """
        Carica configurazione da file YAML.
        
        Args:
            config_path: Path al file YAML (può essere relativo o assoluto)
            validate_adapters: Se True, valida che gli adapter configurati esistano
            
        Returns:
            Dict con configurazione completa (con 'buddy_home' aggiunto)
            
        Raises:
            FileNotFoundError: Se il file non esiste
            yaml.YAMLError: Se c'è un errore di parsing YAML
            ValueError: Se la configurazione non è valida
        """
        # Risolvi il path del config rispetto a BUDDY_HOME
        config_file = resolve_path(config_path)
        
        # Ottieni BUDDY_HOME
        buddy_home = get_buddy_home()
        
        # Se il file non esiste, solleva errore
        if not config_file.exists():
            error_msg = f"Configuration file not found: {config_file} (from: {config_path})"
            logger.error(f"❌ {error_msg}")
            logger.error(f"   BUDDY_HOME: {buddy_home}")
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
            
            # Aggiungi BUDDY_HOME alla configurazione per uso futuro
            config['buddy_home'] = str(buddy_home)
            
            logger.info(f"✅ Configuration loaded from: {config_file}")
            logger.info(f"   BUDDY_HOME: {buddy_home}")
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
        
        registered = AdapterFactory.get_registered_classes()
        
        # Valida input adapters (ora sono liste con 'class')
        if isinstance(config['adapters']['input'], list):
            for adapter_config in config['adapters']['input']:
                class_name = adapter_config.get('class', '')
                
                if class_name not in registered['input']:
                    available = ', '.join(registered['input'])
                    raise ValueError(
                        f"Unknown input adapter class '{class_name}'. "
                        f"Available: {available}"
                    )
        
        # Valida output adapters (ora sono liste con 'class')
        if isinstance(config['adapters']['output'], list):
            for adapter_config in config['adapters']['output']:
                class_name = adapter_config.get('class', '')
            
            # Skip disabled adapters
                
                if class_name not in registered['output']:
                    available = ', '.join(registered['output'])
                    raise ValueError(
                        f"Unknown output adapter class '{class_name}'. "
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
