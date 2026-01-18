"""
Buddy Main - Hexagonal Architecture Orchestrator
Entry point con Event-Driven Architecture e Router Pattern.
"""

import os
import sys
import queue
import logging
from pathlib import Path
from typing import Dict, Any
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

# Core imports
from core import (
    Event, EventType, EventPriority,
    EventRouter, BuddyBrain
)

# Adapters imports
from adapters import AdapterFactory

# Config imports
from config.config_loader import ConfigLoader


# ===== LOGGING SETUP =====
def setup_logging(config: Dict[str, Any]) -> None:
    """
    Configura il sistema di logging
    
    Args:
        config: Configurazione completa di Buddy
    """
    log_config = config['logging']
    buddy_home = Path(config['buddy_home'])
    
    log_file_path = log_config.get('log_file', 'buddy_system.log')
    
    # Risolvi il path del log rispetto a BUDDY_HOME
    log_file = buddy_home / log_file_path if not Path(log_file_path).is_absolute() else Path(log_file_path)
    
    # Crea directory del log se non esiste
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    max_bytes = log_config.get('max_bytes', 10*1024*1024)
    backup_count = log_config.get('backup_count', 3)
    
    handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.addHandler(console_handler)
    
    # Silence noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.INFO)
    logging.getLogger("posthog").setLevel(logging.ERROR)


# ===== MAIN ORCHESTRATOR =====
class BuddyOrchestrator:
    """
    Orchestratore principale di Buddy.
    
    Responsabilità:
    - Setup code e router
    - Inizializzazione Brain
    - Creazione e avvio adapters
    - Main event loop
    - Gestione shutdown
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: Configurazione già caricata e validata
        """
        self.logger = logging.getLogger(__name__)
        self.running = False
        
        # Usa configurazione già caricata
        self.config = config
        self.buddy_home = Path(config['buddy_home'])
        
        # Setup coda di input centralizzata
        queue_config = self.config['queues']
        self.input_queue = queue.PriorityQueue(maxsize=queue_config['input_maxsize'])
        
        # Event Router
        self.router = EventRouter()
        
        # Brain
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment")
        
        self.brain = BuddyBrain(api_key, self.config['brain'])
        
        # Adapters - creati PRIMA del setup routes
        self.input_adapters = []
        self.output_adapters = []
        self._create_adapters()
        
        # Setup routes DOPO aver creato gli adapters
        self._setup_routes()
        
        self.logger.info("🚀 BuddyOrchestrator initialized")
    
    def _setup_routes(self) -> None:
        """
        Configura le route del router in modo DINAMICO interrogando gli adapter output.
        Il routing viene costruito dai metodi handled_events() delle Port.
        Ogni adapter si registra direttamente al router.
        """
        # Registra ogni adapter per gli eventi che gestisce
        for adapter in self.output_adapters:
            handled_events = adapter.__class__.handled_events()
            for event_type in handled_events:
                self.router.register_route(
                    event_type,
                    adapter,
                    adapter.name
                )
        
        # Count unique event types registered
        event_type_count = len(set(
            event_type 
            for adapter in self.output_adapters 
            for event_type in adapter.__class__.handled_events()
        ))
        
        self.logger.info(
            f"📍 Router configured dynamically with {event_type_count} event types "
            f"across {len(self.output_adapters)} adapters"
        )
    
    def _create_adapters(self) -> None:
        """Crea adapters dalla configurazione usando Factory"""
        # Input Adapters - passano input_queue nel costruttore
        for adapter_cfg in self.config['adapters']['input']:
            class_name = adapter_cfg.get('class')
            config = adapter_cfg.get('config', {})
            
            adapter = AdapterFactory.create_input_adapter(
                class_name, 
                config,
                self.input_queue
            )
            if adapter:
                self.input_adapters.append(adapter)
        
        # Output Adapters - autocontenuti con code interne
        for adapter_cfg in self.config['adapters']['output']:
            class_name = adapter_cfg.get('class')
            config = adapter_cfg.get('config', {})
            
            adapter = AdapterFactory.create_output_adapter(class_name, config)
            if adapter:
                self.output_adapters.append(adapter)
        
        self.logger.info(
            f"✅ Adapters created: {len(self.input_adapters)} input, "
            f"{len(self.output_adapters)} output"
        )
    
    def _start_adapters(self) -> None:
        """Avvia tutti gli adapters"""
        # Start input adapters (non ricevono più la coda - ce l'hanno già)
        for adapter in self.input_adapters:
            try:
                adapter.start()
                self.logger.info(f"▶️  Started input adapter: {adapter.name}")
            except Exception as e:
                self.logger.error(f"❌ Failed to start {adapter.name}: {e}")
        
        # Start output adapters (non ricevono più la coda come parametro)
        for adapter in self.output_adapters:
            try:
                adapter.start()
                self.logger.info(f"▶️  Started output adapter: {adapter.name}")
            except Exception as e:
                self.logger.error(f"❌ Failed to start {adapter.name}: {e}")
    
    def _stop_adapters(self) -> None:
        """Ferma tutti gli adapters"""
        self.logger.info("Stopping adapters...")
        
        for adapter in self.input_adapters:
            try:
                adapter.stop()
            except Exception as e:
                self.logger.error(f"Error stopping {adapter.name}: {e}")
        
        for adapter in self.output_adapters:
            try:
                adapter.stop()
            except Exception as e:
                self.logger.error(f"Error stopping {adapter.name}: {e}")
    
    def run(self) -> None:
        """Main event loop"""
        self.running = True
        
        # Avvia adapters
        self._start_adapters()
        
        # Banner
        self._print_banner()
        
        self.logger.info("🧠 Entering main event loop")
        
        try:
            while self.running:
                # Preleva evento input (blocca se vuota, timeout 1s)
                try:
                    queue_item = self.input_queue.get(timeout=1.0)
                    # PriorityQueue contiene (priority, event)
                    if isinstance(queue_item, tuple):
                        _, input_event = queue_item
                    else:
                        input_event = queue_item
                except queue.Empty:
                    continue
                
                # Check shutdown
                if input_event.type == EventType.SHUTDOWN:
                    self.logger.info("Shutdown event received")
                    self.running = False
                    # Processa comunque per salutare se necessario
                
                # Brain processa evento
                output_events = self.brain.process_event(input_event)
                
                # Router smista output events
                self.router.route_events(output_events)
                
                self.input_queue.task_done()
        
        except KeyboardInterrupt:
            self.logger.info("KeyboardInterrupt received")
        
        finally:
            self._shutdown()
    
    def _shutdown(self) -> None:
        """Procedura di shutdown pulita"""
        self.logger.info("🛑 Shutting down Buddy...")
        
        self._stop_adapters()
        
        # Statistiche router
        stats = self.router.get_stats()
        self.logger.info(f"📊 Router stats: {stats}")
        
        self.logger.info("👋 Buddy shutdown complete")
    
    def _print_banner(self) -> None:
        """Stampa banner di avvio"""
        print("\n" + "="*60)
        print("🤖 BUDDY OS - Hexagonal Architecture")
        print("="*60)
        print(f"Brain Model: {self.config['brain']['model_id']}")
        print(f"Input Adapters: {len(self.input_adapters)}")
        print(f"Output Adapters: {len(self.output_adapters)}")
        print("="*60 + "\n")


# ===== ENTRY POINT =====
def main():
    """Entry point principale"""
    
    # Carica variabili d'ambiente
    load_dotenv(".env")
    
    # Carica configurazione (gestisce BUDDY_HOME e BUDDY_CONFIG internamente)
    try:
        config = ConfigLoader.from_env()
    except (ValueError, FileNotFoundError) as e:
        print(f"❌ ERROR: {e}")
        sys.exit(1)
    
    # Setup logging
    setup_logging(config)
    
    logger = logging.getLogger(__name__)
    logger.info(f"🏠 BUDDY_HOME: {config['buddy_home']}")
    logger.info(f"🚀 Starting Buddy with config: {config.get('_config_file', 'unknown')}")
    
    try:
        # Crea e avvia orchestrator
        orchestrator = BuddyOrchestrator(config)
        orchestrator.run()
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
