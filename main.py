"""
Buddy Main - Entry Point
Minimal entry point for Buddy AI Assistant.
"""

import os
import sys
import logging
import logging.config
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

from core import BuddyOrchestrator
from config.config_loader import ConfigLoader


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
    
    # 3. Setup logging, resolve relative log file path against BUDDY_HOME
    logging_config = config['logging']
    log_filename = logging_config['handlers']['file']['filename']
    logging_config['handlers']['file']['filename'] = str(Path(os.getenv('BUDDY_HOME', '.')).resolve() / log_filename)
    
    logging.config.dictConfig(logging_config)
    
    logger = logging.getLogger(__name__)
    logger.info(f"🏠 BUDDY_HOME: {os.getenv('BUDDY_HOME', '.')}")
    logger.info(f"🏠 BUDDY_CONFIG: {os.getenv('BUDDY_CONFIG', '.')}")
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
