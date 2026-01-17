"""
Buddy Main - Hexagonal Architecture Orchestrator
Entry point con Event-Driven Architecture e Router Pattern.
"""

import os
import sys
import time
import queue
import signal
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

# Core imports
from core import (
    Event, EventType, EventPriority, OutputChannel,
    build_event_routing_from_adapters,
    create_input_event, create_output_event,
    EventRouter, BuddyBrain
)

# Adapters imports
from adapters import AdapterFactory

# Config imports
from config.config_loader import ConfigLoader


# ===== LOGGING SETUP =====
def setup_logging(log_config: dict) -> None:
    """Configura il sistema di logging"""
    log_file = log_config.get('log_file', 'buddy_system.log')
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
    
    def __init__(self, config_path: str):
        """
        Args:
            config_path: Path al file di configurazione YAML
        """
        self.logger = logging.getLogger(__name__)
        self.running = False
        
        # Carica configurazione
        self.config = ConfigLoader.load(config_path)
        
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
        # Costruisci routing dinamico dagli adapter configurati
        event_routing = build_event_routing_from_adapters(self.output_adapters)
        
        # Registra ogni adapter per gli eventi che gestisce
        for event_type, channel in event_routing.items():
            # Trova l'adapter che gestisce questo channel
            for adapter in self.output_adapters:
                if adapter.channel_type == channel:
                    self.router.register_route(
                        event_type,
                        adapter,
                        adapter.name
                    )
        
        self.logger.info(
            f"📍 Router configured dynamically with {len(event_routing)} event types "
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
                    input_event = self.input_queue.get(timeout=1.0)
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
    
    # BUDDY_CONFIG è OBBLIGATORIO - fail fast se mancante
    config_file = os.getenv("BUDDY_CONFIG")
    if not config_file:
        print("❌ ERROR: BUDDY_CONFIG environment variable not set")
        print("   Add it to .env file:")
        print("   BUDDY_CONFIG=config/adapter_config_test.yaml")
        sys.exit(1)
    
    # Setup logging
    setup_logging({})
    
    logger = logging.getLogger(__name__)
    logger.info(f"🚀 Starting Buddy with config: {config_file}")
    
    try:
        # Crea orchestrator
        orchestrator = BuddyOrchestrator(config_file)
        
        # Avvia orchestrator
        orchestrator.run()
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
