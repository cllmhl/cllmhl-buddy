"""
Buddy Main - Entry Point
Minimal entry point for Buddy AI Assistant.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

from core import BuddyOrchestrator
from config.config_loader import ConfigLoader


def setup_logging(config: Dict[str, Any]) -> None:
    """
    Configura il sistema di logging.
    
    Args:
        config: Configurazione completa di Buddy
    """
    log_config = config['logging']
    buddy_home = Path(config['buddy_home'])
    
    log_file_path = log_config.get('log_file')
    
    # Risolvi il path del log rispetto a BUDDY_HOME
    log_file = buddy_home / log_file_path
    handler = RotatingFileHandler(
        log_file,
        maxBytes=log_config.get('max_bytes'),
        backupCount=log_config.get('backup_count')
    )
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    handler.setFormatter(formatter)
    
    # Root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    
    # Silence noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.INFO)
    logging.getLogger("posthog").setLevel(logging.ERROR)


def main():
    """Entry point principale."""
    
    # 1. Carica .env per API keys
    env_path = Path(os.getenv('BUDDY_HOME', '.')).resolve() / '.env'
    load_dotenv(env_path)
    
    # 2. Carica configurazione
    try:
        config = ConfigLoader.from_env()
    except (ValueError, FileNotFoundError) as e:
        print(f"❌ ERROR: {e}")
        sys.exit(1)
    
    # 3. Setup logging
    setup_logging(config)
    
    logger = logging.getLogger(__name__)
    logger.info(f"🏠 BUDDY_HOME: {config['buddy_home']}")
    logger.info(f"🚀 Starting Buddy with config: {config.get('_config_file', 'unknown')}")
    
    try:
        # 4. Crea e avvia orchestrator
        orchestrator = BuddyOrchestrator(config)
        orchestrator.run()
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
