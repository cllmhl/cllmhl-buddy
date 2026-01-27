"""
Event Router - Smista eventi agli adapter corretti
Il Brain NON conosce gli output, il Router sì.
"""

import threading
import logging
from typing import Dict, List
from collections import defaultdict

from .events import OutputEvent, OutputEventType

logger = logging.getLogger(__name__)


class EventRouter:
    """
    Router intelligente che smista eventi output agli adapter registrati.
    
    Caratteristiche:
    - Un OutputEventType può avere N destinazioni (broadcast)
    - Thread-safe
    - Statistiche di routing
    - Chiamata diretta su adapter.send_event()
    """
    
    def __init__(self):
        # Mapping: OutputEventType -> List[OutputAdapter]
        self._routes: Dict[OutputEventType, List] = defaultdict(list)
        
        # Lock per operazioni thread-safe
        self._lock = threading.Lock()
        
        # Statistiche
        self._stats = {
            'routed': 0,
            'dropped': 0,
            'no_route': 0
        }
        
        logger.info("📍 EventRouter initialized")
    
    def register_route(
        self,
        event_type: OutputEventType,
        output_adapter,
        adapter_name: str = "unknown"
    ) -> None:
        """
        Registra un output adapter per un tipo di evento.
        
        Args:
            event_type: Tipo di evento da instradare
            output_adapter: Adapter di destinazione (con metodo send_event)
            adapter_name: Nome adapter (per logging)
        """
        with self._lock:
            self._routes[event_type].append(output_adapter)
            
            route_count = len(self._routes[event_type])
            logger.info(
                f"📍 Route registered: {event_type.value} -> "
                f"{adapter_name} (#{route_count})"
            )
    
    
    def route_event(self, event: OutputEvent) -> int:
        """
        Smista un singolo evento a tutti gli adapter registrati.
        
        Returns:
            Numero di destinazioni raggiunte con successo
        """
        with self._lock:
            # Controlla se esiste una route
            if not isinstance(event, OutputEvent):
                logger.warning(f"Cannot route non-output event: {type(event)}")
                return 0
            
            if event.type not in self._routes or not self._routes[event.type]:
                logger.debug(f"⚠️ No route for event: {event.type.value}")
                self._stats['no_route'] += 1
                return 0
            
            routed_count = 0
            
            # Invia a tutti gli adapter registrati
            for output_adapter in self._routes[event.type]:
                try:
                    # Chiama send_event() sull'adapter
                    if output_adapter.send_event(event):
                        routed_count += 1
                        self._stats['routed'] += 1
                    else:
                        # send_event() ha ritornato False (coda piena)
                        self._stats['dropped'] += 1
                    
                except Exception as e:
                    logger.error(
                        f"❌ Error routing to {output_adapter.name}: {e}",
                        exc_info=True
                    )
                    self._stats['dropped'] += 1
            
            return routed_count
    
    def route_events(self, events: List[OutputEvent]) -> int:
        """
        Smista una lista di eventi.
        
        Returns:
            Numero totale di routing effettuati
        """
        total_routed = 0
        for event in events:
            total_routed += self.route_event(event)
        return total_routed
    
    def get_routes(self) -> Dict[OutputEventType, int]:
        """Ritorna il numero di destinazioni per ogni tipo di evento"""
        with self._lock:
            return {
                event_type: len(adapters)
                for event_type, adapters in self._routes.items()
            }
    
    def get_stats(self) -> dict:
        """Statistiche di routing"""
        with self._lock:
            return {
                **self._stats,
                'routes_count': len(self._routes),
                'total_destinations': sum(
                    len(adapters) for adapters in self._routes.values()
                )
            }
    
    def clear_stats(self) -> None:
        """Reset statistiche"""
        with self._lock:
            self._stats = {
                'routed': 0,
                'dropped': 0,
                'no_route': 0
            }
            logger.info("📊 Router stats cleared")
