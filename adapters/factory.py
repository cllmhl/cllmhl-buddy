"""
Adapter Factory - Crea adapter da configurazione
Pattern Factory per instanziare adapter in base al tipo/implementation.
"""

import logging
from typing import Dict, Optional
from queue import PriorityQueue

from .ports import InputPort, OutputPort

logger = logging.getLogger(__name__)


class AdapterFactory:
    """
    Factory per creare adapter Input/Output da configurazione.
    
    Supporta registrazione dinamica di implementazioni.
    """
    
    # Registry delle implementazioni disponibili
    _input_implementations: Dict[str, type] = {}
    _output_implementations: Dict[str, type] = {}
    
    @classmethod
    def register_input(cls, implementation_name: str, adapter_class: type) -> None:
        """
        Registra un'implementazione di InputPort.
        
        Args:
            implementation_name: Nome identificativo (es: "jabra", "mock", "pipe")
            adapter_class: Classe dell'adapter (deve estendere InputPort)
        """
        if not issubclass(adapter_class, InputPort):
            raise ValueError(f"{adapter_class} must extend InputPort")
        
        cls._input_implementations[implementation_name] = adapter_class
        logger.debug(f"📝 Registered input implementation: {implementation_name}")
    
    @classmethod
    def register_output(cls, implementation_name: str, adapter_class: type) -> None:
        """
        Registra un'implementazione di OutputPort.
        
        Args:
            implementation_name: Nome identificativo (es: "jabra", "log", "gpio")
            adapter_class: Classe dell'adapter (deve estendere OutputPort)
        """
        if not issubclass(adapter_class, OutputPort):
            raise ValueError(f"{adapter_class} must extend OutputPort")
        
        cls._output_implementations[implementation_name] = adapter_class
        logger.debug(f"📝 Registered output implementation: {implementation_name}")
    
    @classmethod
    def create_input_adapter(
        cls,
        adapter_type: str,
        config: dict
    ) -> Optional[InputPort]:
        """
        Crea un input adapter dalla configurazione.
        
        Args:
            adapter_type: Tipo di adapter (es: "voice", "keyboard", "sensor")
            config: Dict con:
                - implementation: Nome implementazione (es: "jabra", "mock")
                - config: Configurazione specifica dell'adapter
        
        Returns:
            Istanza di InputPort o None se disabled/errore
        """
        implementation = config.get('implementation', '').lower()
        
        # Check se disabilitato
        if implementation == 'disabled':
            logger.info(f"⏭️  Input adapter '{adapter_type}' disabled in config")
            return None
        
        # Cerca implementazione nel registry
        if implementation not in cls._input_implementations:
            logger.error(
                f"❌ Unknown input implementation: '{implementation}' "
                f"for adapter '{adapter_type}'"
            )
            logger.info(f"Available implementations: {list(cls._input_implementations.keys())}")
            return None
        
        try:
            # Crea istanza
            adapter_class = cls._input_implementations[implementation]
            adapter_config = config.get('config', {})
            
            adapter = adapter_class(
                name=f"{adapter_type}_{implementation}",
                config=adapter_config
            )
            
            logger.info(f"✅ Created input adapter: {adapter.name}")
            return adapter
            
        except Exception as e:
            logger.error(
                f"❌ Failed to create input adapter '{adapter_type}' "
                f"(implementation: '{implementation}'): {e}",
                exc_info=True  # Include full stack trace
            )
            # Fail-fast: propaga l'errore invece di ritornare None
            raise RuntimeError(
                f"Input adapter creation failed: {adapter_type}/{implementation}"
            ) from e
    
    @classmethod
    def create_output_adapter(
        cls,
        adapter_type: str,
        config: dict
    ) -> Optional[OutputPort]:
        """
        Crea un output adapter dalla configurazione.
        
        Args:
            adapter_type: Tipo di adapter (es: "voice", "led", "database")
            config: Dict con:
                - implementation: Nome implementazione (es: "jabra", "log", "gpio")
                - config: Configurazione specifica dell'adapter
        
        Returns:
            Istanza di OutputPort o None se disabled/errore
        """
        implementation = config.get('implementation', '').lower()
        
        # Check se disabilitato
        if implementation == 'disabled':
            logger.info(f"⏭️  Output adapter '{adapter_type}' disabled in config")
            return None
        
        # Cerca implementazione nel registry
        if implementation not in cls._output_implementations:
            logger.error(
                f"❌ Unknown output implementation: '{implementation}' "
                f"for adapter '{adapter_type}'"
            )
            logger.info(f"Available implementations: {list(cls._output_implementations.keys())}")
            return None
        
        try:
            # Crea istanza
            adapter_class = cls._output_implementations[implementation]
            adapter_config = config.get('config', {})
            
            adapter = adapter_class(
                name=f"{adapter_type}_{implementation}",
                config=adapter_config
            )
            
            logger.info(f"✅ Created output adapter: {adapter.name}")
            return adapter
            
        except Exception as e:
            logger.error(
                f"❌ Failed to create output adapter '{adapter_type}' "
                f"(implementation: '{implementation}'): {e}",
                exc_info=True  # Include full stack trace
            )
            # Fail-fast: propaga l'errore invece di ritornare None
            raise RuntimeError(
                f"Output adapter creation failed: {adapter_type}/{implementation}"
            ) from e
    
    @classmethod
    def get_registered_implementations(cls) -> dict:
        """Ritorna tutte le implementazioni registrate"""
        return {
            'input': list(cls._input_implementations.keys()),
            'output': list(cls._output_implementations.keys())
        }
