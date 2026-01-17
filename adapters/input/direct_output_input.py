"""
Direct Output Input Adapter
Genera eventi DIRECT_OUTPUT configurabili per testare output hardware.

Utile per test hardware output mantenendo la stessa filosofia dei test input:
- Configurazione YAML
- Esecuzione via main.py
- Brain passa-through (unwrap DIRECT_OUTPUT)
- Output adapter reale testato
"""

import logging
import threading
import time
from queue import PriorityQueue
from typing import List, Dict, Any

from adapters.ports import InputPort
from core.events import (
    Event, EventType, EventPriority, 
    create_input_event, create_output_event
)

logger = logging.getLogger(__name__)


class DirectOutputInput(InputPort):
    """
    Input adapter che genera eventi DIRECT_OUTPUT da configurazione.
    
    Modalità supportate:
    1. sequence: Lista di eventi da generare in sequenza
    2. interactive: Menu interattivo per scegliere eventi
    3. loop: Ripete una sequenza continuamente
    """
    
    def __init__(self, name: str, config: dict, input_queue: PriorityQueue):
        super().__init__(name, config, input_queue)
        
        # Modalità operativa
        self.mode = config.get('mode', 'interactive')  # sequence, interactive, loop
        
        # Sequenza eventi (per mode=sequence o loop)
        self.sequence = config.get('sequence', [])
        
        # Loop settings
        self.loop_delay = config.get('loop_delay', 5.0)
        self.loop_count = config.get('loop_count', None)  # None = infinito
        
        # Thread worker
        self.worker_thread = None
        
        logger.info(
            f"🎯 DirectOutputInput initialized (mode: {self.mode}, "
            f"sequence: {len(self.sequence)} events)"
        )
    
    def start(self):
        self.running = True
        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name=f"{self.name}_worker"
        )
        self.worker_thread.start()
        logger.info(f"▶️  {self.name} started")
    
    def stop(self):
        self.running = False
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=2.0)
        logger.info(f"⏹️  {self.name} stopped")
    
    def _worker_loop(self):
        """Loop principale basato su mode"""
        if self.mode == 'sequence':
            self._run_sequence_mode()
        elif self.mode == 'loop':
            self._run_loop_mode()
        elif self.mode == 'interactive':
            self._run_interactive_mode()
        else:
            logger.error(f"Unknown mode: {self.mode}")
    
    def _run_sequence_mode(self):
        """
        Esegue una sequenza di eventi una volta e poi termina.
        Utile per test automatici.
        """
        logger.info(f"🎬 Starting sequence: {len(self.sequence)} events")
        
        for idx, event_spec in enumerate(self.sequence, 1):
            if not self.running:
                break
            
            logger.info(f"▶️  Event {idx}/{len(self.sequence)}: {event_spec.get('type')}")
            
            # Genera evento
            self._generate_event(event_spec)
            
            # Delay se specificato
            delay = event_spec.get('delay', 0)
            if delay > 0 and self.running:
                time.sleep(delay)
        
        logger.info("✅ Sequence completed")
    
    def _run_loop_mode(self):
        """
        Ripete la sequenza in loop.
        Utile per stress test o demo.
        """
        iteration = 0
        logger.info(
            f"🔄 Starting loop mode: {len(self.sequence)} events, "
            f"delay: {self.loop_delay}s"
        )
        
        while self.running:
            iteration += 1
            
            # Check loop count limit
            if self.loop_count and iteration > self.loop_count:
                logger.info(f"✅ Loop completed ({iteration-1} iterations)")
                break
            
            logger.info(f"🔄 Loop iteration {iteration}")
            
            # Esegui sequenza
            for event_spec in self.sequence:
                if not self.running:
                    break
                self._generate_event(event_spec)
                delay = event_spec.get('delay', 0)
                if delay > 0:
                    time.sleep(delay)
            
            # Delay tra iterazioni
            if self.running and self.loop_delay > 0:
                time.sleep(self.loop_delay)
    
    def _run_interactive_mode(self):
        """
        Menu interattivo per generare eventi manualmente.
        Utile per test manuali esploratori.
        """
        print("\n" + "="*60)
        print("DirectOutputInput - Interactive Mode")
        print("="*60)
        print("\nComandi disponibili:")
        print("  1) LED ascolto ON")
        print("  2) LED ascolto OFF")
        print("  3) LED stato ON")
        print("  4) LED stato OFF")
        print("  5) LED blink ascolto (3x)")
        print("  6) LED blink stato (5x)")
        print("  7) TTS test")
        print("  8) TTS custom")
        print("  q) Quit")
        print("="*60 + "\n")
        
        while self.running:
            try:
                choice = input("Scegli comando > ").strip().lower()
                
                if choice == 'q':
                    logger.info("Interactive mode terminated by user")
                    break
                
                self._handle_interactive_command(choice)
                
            except EOFError:
                break
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Interactive mode error: {e}")
                print(f"❌ Errore: {e}")
    
    def _handle_interactive_command(self, choice: str):
        """Gestisce comandi interattivi"""
        commands = {
            '1': {'type': 'LED_ON', 'metadata': {'led': 'ascolto'}},
            '2': {'type': 'LED_OFF', 'metadata': {'led': 'ascolto'}},
            '3': {'type': 'LED_ON', 'metadata': {'led': 'stato'}},
            '4': {'type': 'LED_OFF', 'metadata': {'led': 'stato'}},
            '5': {'type': 'LED_BLINK', 'metadata': {'led': 'ascolto', 'times': 3}},
            '6': {'type': 'LED_BLINK', 'metadata': {'led': 'stato', 'times': 5}},
            '7': {'type': 'SPEAK', 'content': 'Ciao, questo è un test di output vocale.'},
        }
        
        if choice == '8':
            # TTS custom
            text = input("Inserisci testo da pronunciare: ").strip()
            if text:
                self._generate_event({'type': 'SPEAK', 'content': text})
                print(f"✅ TTS: {text}")
        elif choice in commands:
            self._generate_event(commands[choice])
            event_type = commands[choice]['type']
            print(f"✅ Evento generato: {event_type}")
        else:
            print("❌ Comando non valido")
    
    def _generate_event(self, event_spec: Dict[str, Any]):
        """
        Genera un evento DIRECT_OUTPUT dalla specifica.
        
        event_spec formato:
        {
            'type': 'LED_ON',           # EventType name
            'content': None,            # Optional content
            'metadata': {'led': 'ascolto'},
            'priority': 'HIGH'          # Optional
        }
        """
        try:
            # Parse event type
            event_type_name = event_spec.get('type')
            if not event_type_name:
                logger.error("Event spec missing 'type'")
                return
            
            try:
                event_type = EventType[event_type_name]
            except KeyError:
                logger.error(f"Unknown event type: {event_type_name}")
                return
            
            # Parse priority
            priority_name = event_spec.get('priority', 'HIGH')
            try:
                priority = EventPriority[priority_name]
            except KeyError:
                priority = EventPriority.HIGH
            
            # Crea evento output interno
            inner_event = create_output_event(
                event_type=event_type,
                content=event_spec.get('content'),
                priority=priority,
                metadata=event_spec.get('metadata', {})
            )
            
            # Wrappa in DIRECT_OUTPUT
            wrapper_event = create_input_event(
                event_type=EventType.DIRECT_OUTPUT,
                content=inner_event,
                source=self.name,
                priority=priority
            )
            
            # Invia alla coda
            self.input_queue.put((wrapper_event.priority.value, wrapper_event))
            
            logger.debug(
                f"📤 Generated DIRECT_OUTPUT: {event_type.value} "
                f"(content: {str(event_spec.get('content', 'None'))[:30]})"
            )
            
        except Exception as e:
            logger.error(f"Error generating event: {e}", exc_info=True)
