"""
Event Router - Smista eventi agli adapter corretti
Il Brain NON conosce gli output, il Router sì.
"""

import queue
import threading
import logging
from typing import Dict, List, Optional
from collections import defaultdict

from .events import Event, EventType

logger = logging.getLogger(__name__)


class EventRouter:
    """
    Router intelligente che smista eventi output agli adapter registrati.
    
    Caratteristiche:
    - Un EventType può avere N destinazioni (broadcast)
    - Thread-safe
    - Statistiche di routing
    - Gestione code piene
    """
    
    def __init__(self):
        # Mapping: EventType -> List[Queue]
        self._routes: Dict[EventType, List[queue.PriorityQueue]] = defaultdict(list)
        
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
        event_type: EventType,
        output_queue: queue.PriorityQueue,
        adapter_name: str = "unknown"
    ) -> None:
        """
        Registra un output adapter per un tipo di evento.
        
        Args:
            event_type: Tipo di evento da instradare
            output_queue: Coda dell'adapter di destinazione
            adapter_name: Nome adapter (per logging)
        """
        with self._lock:
            self._routes[event_type].append(output_queue)
            
            route_count = len(self._routes[event_type])
            logger.info(
                f"📍 Route registered: {event_type.value} -> "
                f"{adapter_name} (#{route_count})"
            )
    
    def unregister_route(
        self,
        event_type: EventType,
        output_queue: queue.PriorityQueue
    ) -> bool:
        """Rimuove una route registrata"""
        with self._lock:
            if event_type in self._routes:
                try:
                    self._routes[event_type].remove(output_queue)
                    logger.info(f"📍 Route unregistered: {event_type.value}")
                    return True
                except ValueError:
                    pass
        return False
    
    def route_event(self, event: Event) -> int:
        """
        Smista un singolo evento a tutti gli adapter registrati.
        
        Returns:
            Numero di destinazioni raggiunte con successo
        """
        with self._lock:
            # Controlla se esiste una route
            if event.type not in self._routes or not self._routes[event.type]:
                logger.debug(f"⚠️ No route for event: {event.type.value}")
                self._stats['no_route'] += 1
                return 0
            
            routed_count = 0
            
            # Invia a tutte le destinazioni registrate
            for output_queue in self._routes[event.type]:
                try:
                    # Non bloccare se la coda è piena
                    output_queue.put(event, block=False)
                    routed_count += 1
                    self._stats['routed'] += 1
                    
                except queue.Full:
                    logger.error(
                        f"❌ Queue FULL for {event.type.value}! "
                        f"Event dropped: {event.content}"
                    )
                    self._stats['dropped'] += 1
            
            return routed_count
    
    def route_events(self, events: List[Event]) -> int:
        """
        Smista una lista di eventi.
        
        Returns:
            Numero totale di routing effettuati
        """
        total_routed = 0
        for event in events:
            total_routed += self.route_event(event)
        return total_routed
    
    def get_routes(self) -> Dict[EventType, int]:
        """Ritorna il numero di destinazioni per ogni tipo di evento"""
        with self._lock:
            return {
                event_type: len(queues)
                for event_type, queues in self._routes.items()
            }
    
    def get_stats(self) -> dict:
        """Statistiche di routing"""
        with self._lock:
            return {
                **self._stats,
                'routes_count': len(self._routes),
                'total_destinations': sum(
                    len(queues) for queues in self._routes.values()
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
