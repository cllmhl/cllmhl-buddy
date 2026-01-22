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
from core.events import Event, InputEventType, OutputEventType, EventPriority, create_input_event
from core.event_router import EventRouter
from core.brain import BuddyBrain
from core.commands import AdapterCommand

# Adapters imports
from adapters.factory import AdapterFactory

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
        self._interrupt_handler_thread: threading.Thread | None = None
        
        # Event Router
        self.router = EventRouter()
        
        # Brain
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment")
        
        self.brain = BuddyBrain(api_key, self.config['brain'])
        
        # Adapters - creati PRIMA del setup routes
        self.input_adapters: List[InputPort] = []
        self.output_adapters: List[OutputPort] = []
        self._create_adapters()
        
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
        for adapter in self.output_adapters:
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
            for adapter in self.output_adapters 
            for event_type in type(adapter).handled_events()
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
                self.input_queue,
                self.interrupt_queue
            )
            if adapter:
                self.input_adapters.append(adapter)
        
        # Output Adapters - autocontenuti con code interne
        for adapter_cfg in self.config['adapters']['output']:
            class_name = adapter_cfg.get('class')
            config = adapter_cfg.get('config', {})
            
            output_adapter = AdapterFactory.create_output_adapter(class_name, config)
            if output_adapter:
                self.output_adapters.append(output_adapter)
        
        self.logger.info(
            f"✅ Adapters created: {len(self.input_adapters)} input, "
            f"{len(self.output_adapters)} output"
        )
    
    def _start_adapters(self) -> None:
        """Avvia tutti gli adapters"""
        # Start input adapters (non ricevono più la coda - ce l'hanno già)
        for in_adapter in self.input_adapters:
            try:
                in_adapter.start()
                self.logger.info(f"▶️  Started input adapter: {in_adapter.name}")
            except Exception as e:
                self.logger.error(f"❌ Failed to start {in_adapter.name}: {e}")
        
        # Start output adapters (non ricevono più la coda come parametro)
        for out_adapter in self.output_adapters:
            try:
                out_adapter.start()
                self.logger.info(f"▶️  Started output adapter: {out_adapter.name}")
            except Exception as e:
                self.logger.error(f"❌ Failed to start {out_adapter.name}: {e}")
    
    def _stop_adapters(self) -> None:
        """Ferma tutti gli adapters"""
        self.logger.info("Stopping adapters...")
        
        for in_adapter in self.input_adapters:
            try:
                in_adapter.stop()
            except Exception as e:
                self.logger.error(f"Error stopping {in_adapter.name}: {e}")
        
        for out_adapter in self.output_adapters:
            try:
                out_adapter.stop()
            except Exception as e:
                self.logger.error(f"Error stopping {out_adapter.name}: {e}")
    
    def run(self) -> None:
        """Main event loop"""
        self.running = True
        
        # Avvia adapters
        self._start_adapters()
        
        # Avvia interrupt handler thread
        self._interrupt_handler_thread = threading.Thread(target=self._interrupt_handler_loop, daemon=True)
        self._interrupt_handler_thread.start()
        
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
                    # Timeout - nessuna coda. Controlliamo i timer.
                    timer_events = self.brain.check_timers()
                    if timer_events:
                        self.router.route_events(timer_events)
                    continue
                
                # Check shutdown
                if input_event.type == InputEventType.SHUTDOWN:
                    self.logger.info("Shutdown event received")
                    self.running = False
                    # Processa comunque per salutare se necessario
                
                # Brain processa evento → (eventi, comandi)
                output_events, adapter_commands = self.brain.process_event(input_event)
                
                # PRIMA: Esegui comandi SINCRONI (stabilisci stato adapter)
                self._execute_commands(adapter_commands)
                
                # POI: Router smista output events (asincroni)
                self.router.route_events(output_events)
                
                self.input_queue.task_done()
        
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}", exc_info=True)
        
        finally:
            self._shutdown()
    
    def _execute_commands(self, commands: List[AdapterCommand]) -> None:
        """
        Esegue comandi adapter SINCRONAMENTE broadcast a tutti gli adapter.
        
        Ogni adapter decide se gestire o ignorare il comando basandosi
        su supported_commands(). Non c'è routing - tutti ricevono tutti i comandi.
        
        Args:
            commands: Lista di comandi da eseguire
        """
        if not commands:
            return
        
        for command in commands:
            handled_count = 0
            
            # Broadcast a TUTTI gli input adapter
            for adapter in self.input_adapters:
                try:
                    if adapter.handle_command(command):
                        handled_count += 1
                        self.logger.debug(f"✅ {adapter.name} handled {command.value}")
                except Exception as e:
                    self.logger.error(
                        f"❌ Error executing {command.value} on {adapter.name}: {e}",
                        exc_info=True
                    )
            
            # Broadcast a TUTTI gli output adapter
            for adapter in self.output_adapters:
                try:
                    if adapter.handle_command(command):
                        handled_count += 1
                        self.logger.debug(f"✅ {adapter.name} handled {command.value}")
                except Exception as e:
                    self.logger.error(
                        f"❌ Error executing {command.value} on {adapter.name}: {e}",
                        exc_info=True
                    )
            
            if handled_count == 0:
                self.logger.warning(f"⚠️  Command {command.value} not handled by any adapter")
            else:
                self.logger.info(f"🎯 Command {command.value} handled by {handled_count} adapter(s)")

    def _interrupt_handler_loop(self) -> None:
        """
        Loop del thread di interruzione.
        Ascolta sulla interrupt_queue e agisce immediatamente.
        """
        self.logger.info("🚨 Interrupt handler thread started")
        while self.running:
            try:
                interrupt_event = self.interrupt_queue.get(timeout=1.0)
                
                if interrupt_event.type == InputEventType.INTERRUPT:
                    self.logger.warning(f"⚡ INTERRUPT received: {interrupt_event.content}")
                    
                    # 1. Ferma immediatamente l'output vocale
                    for adapter in self.output_adapters:
                        if "VoiceOutput" in adapter.name:
                            adapter.handle_command(AdapterCommand.VOICE_OUTPUT_STOP)
                            
                    # 2. Inserisci l'evento di interruzione nella coda principale per l'elaborazione
                    event = create_input_event(
                        InputEventType.USER_SPEECH,
                        interrupt_event.content,
                        source="interrupt",
                        priority=EventPriority.HIGH
                    )
                    self.input_queue.put(event)
                
                self.interrupt_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error in interrupt handler loop: {e}", exc_info=True)
    
    def _shutdown(self) -> None:
        """Procedura di shutdown pulita"""
        self.logger.info("🛑 Shutting down Buddy...")
        
        # Disabilita flag running prima di stop
        self.running = False
        
        self._stop_adapters()
        
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
        print(f"Input Adapters: {len(self.input_adapters)}")
        print(f"Output Adapters: {len(self.output_adapters)}")
        print("="*60 + "\n")
