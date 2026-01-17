"""
Adapter Factory - Crea adapter da configurazione
Pattern Factory per instanziare adapter dal nome diretto della classe.
"""

import logging
from typing import Optional
from queue import PriorityQueue

from .ports import InputPort, OutputPort

logger = logging.getLogger(__name__)


class AdapterFactory:
    """
    Factory per creare adapter Input/Output da configurazione.
    
    Supporta registrazione dinamica di classi adapter.
    """
    
    # Registry delle classi disponibili
    _input_classes: dict[str, type] = {}
    _output_classes: dict[str, type] = {}
    
    @classmethod
    def register_input(cls, class_name: str, adapter_class: type) -> None:
        """
        Registra una classe di InputPort.
        
        Args:
            class_name: Nome della classe (es: "MockVoiceInput", "JabraVoiceInput")
            adapter_class: Classe dell'adapter (deve estendere InputPort)
        """
        if not issubclass(adapter_class, InputPort):
            raise ValueError(f"{adapter_class} must extend InputPort")
        
        cls._input_classes[class_name] = adapter_class
        logger.debug(f"📝 Registered input class: {class_name}")
    
    @classmethod
    def register_output(cls, class_name: str, adapter_class: type) -> None:
        """
        Registra una classe di OutputPort.
        
        Args:
            class_name: Nome della classe (es: "MockVoiceOutput", "JabraVoiceOutput")
            adapter_class: Classe dell'adapter (deve estendere OutputPort)
        """
        if not issubclass(adapter_class, OutputPort):
            raise ValueError(f"{adapter_class} must extend OutputPort")
        
        cls._output_classes[class_name] = adapter_class
        logger.debug(f"📝 Registered output class: {class_name}")
    
    @classmethod
    def create_input_adapter(
        cls,
        class_name: str,
        config: dict,
        input_queue: PriorityQueue
    ) -> Optional[InputPort]:
        """
        Crea un input adapter dalla configurazione.
        
        Args:
            class_name: Nome della classe (es: "MockVoiceInput")
            config: Configurazione specifica dell'adapter
            input_queue: Coda centralizzata per gli eventi
        
        Returns:
            Istanza di InputPort o None se errore
        """
        # Cerca classe nel registry
        if class_name not in cls._input_classes:
            logger.error(
                f"❌ Unknown input class: '{class_name}'"
            )
            logger.info(f"Available classes: {list(cls._input_classes.keys())}")
            return None
        
        try:
            # Crea istanza
            adapter_class = cls._input_classes[class_name]
            
            adapter = adapter_class(
                name=class_name,
                config=config,
                input_queue=input_queue
            )
            
            logger.info(f"✅ Created input adapter: {adapter.name}")
            return adapter
            
        except Exception as e:
            logger.error(
                f"❌ Failed to create input adapter '{class_name}': {e}",
                exc_info=True
            )
            raise RuntimeError(
                f"Input adapter creation failed: {class_name}"
            ) from e
    
    @classmethod
    def create_output_adapter(
        cls,
        class_name: str,
        config: dict
    ) -> Optional[OutputPort]:
        """
        Crea un output adapter dalla configurazione.
        
        Args:
            class_name: Nome della classe (es: "MockVoiceOutput")
            config: Configurazione specifica dell'adapter (include queue_maxsize)
        
        Returns:
            Istanza di OutputPort o None se errore
        """
        # Cerca classe nel registry
        if class_name not in cls._output_classes:
            logger.error(
                f"❌ Unknown output class: '{class_name}'"
            )
            logger.info(f"Available classes: {list(cls._output_classes.keys())}")
            return None
        
        try:
            # Crea istanza
            adapter_class = cls._output_classes[class_name]
            
            adapter = adapter_class(
                name=class_name,
                config=config
            )
            
            logger.info(f"✅ Created output adapter: {adapter.name}")
            return adapter
            
        except Exception as e:
            logger.error(
                f"❌ Failed to create output adapter '{class_name}': {e}",
                exc_info=True
            )
            raise RuntimeError(
                f"Output adapter creation failed: {class_name}"
            ) from e
    
    @classmethod
    def get_registered_classes(cls) -> dict:
        """Ritorna tutte le classi registrate"""
        return {
            'input': list(cls._input_classes.keys()),
            'output': list(cls._output_classes.keys())
        }
