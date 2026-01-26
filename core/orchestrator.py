from __future__ import annotations

"""
Buddy Orchestrator - Core Component
Orchestrates the main event loop and lifecycle of Buddy system.
"""

import os
import queue
import signal
import logging
import threading
from pathlib import Path
from typing import Dict, Any, List, TYPE_CHECKING

# Core imports
from core.events import InputEvent, OutputEvent, InputEventType, OutputEventType, EventPriority, create_input_event
from core.event_router import EventRouter
from core.brain import BuddyBrain
from core.commands import AdapterCommand
import core.tools as tools


# AdapterManager import
from core.adapter_manager import AdapterManager

if TYPE_CHECKING:
    from adapters.ports import InputPort, OutputPort


class BuddyOrchestrator:
    """
    Orchestratore principale di Buddy.
    
    Responsabilità:
    - Setup core e router
    - Inizializzazione Brain
    - Creazione e avvio adapters
    - Main event loop
    - Gestione shutdown
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: Configurazione già caricata e validata
        
        Raises:
            ValueError: Se GOOGLE_API_KEY non è settata nell'environment
        """
        self.logger = logging.getLogger(__name__)
        self.running = False
        
        # Setup signal handlers per shutdown pulito
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Usa configurazione già caricata
        self.config = config
        self.buddy_home = Path(config['buddy_home'])
        
        # Setup coda di input centralizzata
        queue_config = self.config['queues']
        self.input_queue: queue.PriorityQueue = queue.PriorityQueue(maxsize=queue_config['input_maxsize'])
        self.interrupt_queue: queue.Queue = queue.Queue(maxsize=queue_config.get('interrupt_maxsize', 10))

        # Inject queue into tools
        tools.set_input_queue(self.input_queue)

        # Event Router
        self.router = EventRouter()

        # Brain
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment")

        self.brain = BuddyBrain(api_key, self.config['brain'])

        # AdapterManager handles all adapter logic
        self.adapter_manager = AdapterManager(
            self.config,
            self.input_queue,
            self.interrupt_queue,
            self.logger
        )
        self.adapter_manager.create_adapters()

        # Setup routes DOPO aver creato gli adapters
        self._setup_routes()

        self.logger.info("🚀 BuddyOrchestrator initialized")
    
    def _signal_handler(self, signum, frame):
        """Handler per SIGINT (CTRL-C) e SIGTERM"""
        sig_name = 'SIGINT' if signum == signal.SIGINT else 'SIGTERM'
        self.logger.info(f"⚠️  {sig_name} received, shutting down...")
        self.running = False
    
    def _setup_routes(self) -> None:
        """
        Configura le route del router in modo DINAMICO interrogando gli adapter output.
        Il routing viene costruito dai metodi handled_events() delle Port.
        Ogni adapter si registra direttamente al router.
        """
        # Registra ogni adapter per gli eventi che gestisce
        for adapter in self.adapter_manager.output_adapters:
            handled_events = type(adapter).handled_events()
            for event_type in handled_events:
                self.router.register_route(
                    event_type,
                    adapter,
                    adapter.name
                )

        # Count unique event types registered
        event_type_count = len(set(
            event_type
            for adapter in self.adapter_manager.output_adapters
            for event_type in type(adapter).handled_events()
        ))

        self.logger.info(
            f"📍 Router configured dynamically with {event_type_count} event types "
            f"across {len(self.adapter_manager.output_adapters)} adapters"
        )

    
    def run(self) -> None:
        """Main event loop"""
        self.running = True

        # Avvia adapters
        self.adapter_manager.start_adapters()

        # Avvia interrupt handler thread tramite AdapterManager
        self.adapter_manager.start_interrupt_handler(lambda: self.running)

        # Banner
        self._print_banner()

        self.logger.info("🧠 Entering main event loop")

        try:
            while self.running:
                # Preleva evento input (blocca se vuota, timeout 1s)
                try:
                    queue_item = self.input_queue.get(timeout=1.0)
                    input_event: InputEvent

                    # PriorityQueue contiene (priority, event)
                    if isinstance(queue_item, tuple):
                        _, input_event = queue_item
                    else:
                        input_event = queue_item
                except queue.Empty:
                    # Timeout - nessuna coda. Controlliamo i timer.
                    timer_events = self.brain.check_timers()
                    if timer_events:
                        self.router.route_events(timer_events)
                    continue

                # 1. Orchestration Logic: AdapterManager handles system commands
                self.adapter_manager.handle_event(input_event)

                # 2. Business Logic: Brain processa evento
                output_events = self.brain.process_event(input_event)

                # 3. Routing: Smista output events
                self.router.route_events(output_events)

                self.input_queue.task_done()

        except Exception as e:
            self.logger.error(f"Error in main loop: {e}", exc_info=True)

        finally:
            self._shutdown()
    
    # System command logic now handled by AdapterManager.handle_event

    
    def _shutdown(self) -> None:
        """Procedura di shutdown pulita"""
        self.logger.info("🛑 Shutting down Buddy...")
        
        # Disabilita flag running prima di stop
        self.running = False
        
        self.adapter_manager.stop_adapters()
        
        # Statistiche router
        try:
            stats = self.router.get_stats()
            self.logger.info(f"📊 Router stats: {stats}")
        except Exception as e:
            self.logger.warning(f"Could not get router stats: {e}")
        
        self.logger.info("👋 Buddy shutdown complete")
    
    def _print_banner(self) -> None:
        """Stampa banner di avvio"""
        print("\n" + "="*60)
        print("🤖 BUDDY OS - Hexagonal Architecture")
        print("="*60)
        print(f"Brain Model: {self.config['brain']['model_id']}")
        print(f"Input Adapters: {len(self.adapter_manager.input_adapters)}")
        print(f"Output Adapters: {len(self.adapter_manager.output_adapters)}")
        print("="*60 + "\n")
