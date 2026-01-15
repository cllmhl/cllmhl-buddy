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
    Event, EventType, EventPriority,
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
        
        # Setup code con priorità
        queue_config = self.config['queues']
        self.input_queue = queue.PriorityQueue(maxsize=queue_config['input_maxsize'])
        
        # Code output (una per canale)
        self.voice_queue = queue.PriorityQueue(maxsize=queue_config['voice_maxsize'])
        self.led_queue = queue.PriorityQueue(maxsize=queue_config['led_maxsize'])
        self.database_queue = queue.PriorityQueue(maxsize=queue_config['database_maxsize'])
        self.log_queue = queue.PriorityQueue(maxsize=queue_config['log_maxsize'])
        
        # Event Router
        self.router = EventRouter()
        self._setup_routes()
        
        # Brain
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment")
        
        self.brain = BuddyBrain(api_key, self.config['brain'])
        
        # Adapters
        self.input_adapters = []
        self.output_adapters = []
        
        self.logger.info("🚀 BuddyOrchestrator initialized")
    
    def _setup_routes(self) -> None:
        """Configura le route del router"""
        # Route per SPEAK
        self.router.register_route(EventType.SPEAK, self.voice_queue, "voice_output")
        
        # Route per LED
        self.router.register_route(EventType.LED_ON, self.led_queue, "led_output")
        self.router.register_route(EventType.LED_OFF, self.led_queue, "led_output")
        self.router.register_route(EventType.LED_BLINK, self.led_queue, "led_output")
        
        # Route per Database
        self.router.register_route(EventType.SAVE_HISTORY, self.database_queue, "database_output")
        self.router.register_route(EventType.SAVE_MEMORY, self.database_queue, "database_output")
        
        # Route per Logging
        self.router.register_route(EventType.LOG_DEBUG, self.log_queue, "log_output")
        self.router.register_route(EventType.LOG_INFO, self.log_queue, "log_output")
        self.router.register_route(EventType.LOG_WARNING, self.log_queue, "log_output")
        self.router.register_route(EventType.LOG_ERROR, self.log_queue, "log_output")
        
        self.logger.info("📍 Router routes configured")
    
    def _create_adapters(self) -> None:
        """Crea adapters dalla configurazione usando Factory"""
        # Input Adapters
        for name, cfg in self.config['adapters']['input'].items():
            adapter = AdapterFactory.create_input_adapter(name, cfg)
            if adapter:
                self.input_adapters.append(adapter)
        
        # Output Adapters
        output_queue_map = {
            'voice': self.voice_queue,
            'led': self.led_queue,
            'database': self.database_queue,
            'log': self.log_queue
        }
        
        for name, cfg in self.config['adapters']['output'].items():
            adapter = AdapterFactory.create_output_adapter(name, cfg)
            if adapter and name in output_queue_map:
                self.output_adapters.append((adapter, output_queue_map[name]))
        
        self.logger.info(
            f"✅ Adapters created: {len(self.input_adapters)} input, "
            f"{len(self.output_adapters)} output"
        )
    
    def _start_adapters(self) -> None:
        """Avvia tutti gli adapters"""
        # Start input adapters
        for adapter in self.input_adapters:
            try:
                adapter.start(self.input_queue)
                self.logger.info(f"▶️  Started input adapter: {adapter.name}")
            except Exception as e:
                self.logger.error(f"❌ Failed to start {adapter.name}: {e}")
        
        # Start output adapters
        for adapter, output_queue in self.output_adapters:
            try:
                adapter.start(output_queue)
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
        
        for adapter, _ in self.output_adapters:
            try:
                adapter.stop()
            except Exception as e:
                self.logger.error(f"Error stopping {adapter.name}: {e}")
    
    def run(self) -> None:
        """Main event loop"""
        self.running = True
        
        # Crea e avvia adapters
        self._create_adapters()
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
    import argparse
    
    # Parse arguments
    parser = argparse.ArgumentParser(description='Buddy AI Assistant - Hexagonal Architecture')
    parser.add_argument('--config', type=str, help='Path to configuration file')
    parser.add_argument('--dry-run', action='store_true', help='Initialize and exit (test configuration)')
    args = parser.parse_args()
    
    # Carica variabili d'ambiente
    load_dotenv("config.env")
    load_dotenv(".env")
    
    # Determina quale config usare
    config_file = args.config or os.getenv(
        "BUDDY_CONFIG",
        "config/adapter_config_test.yaml"
    )
    
    # Setup logging (con defaults se config non disponibile)
    setup_logging({})
    
    logger = logging.getLogger(__name__)
    logger.info(f"🚀 Starting Buddy with config: {config_file}")
    
    try:
        # Crea orchestrator
        orchestrator = BuddyOrchestrator(config_file)
        
        if args.dry_run:
            logger.info("✅ Dry-run successful. Exiting.")
            sys.exit(0)
        
        # Avvia orchestrator
        orchestrator.run()
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
