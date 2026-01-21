"""
Adapter Factory - Crea adapter da configurazione
Pattern Factory per instanziare adapter dal nome diretto della classe.
Fail-fast: solleva eccezioni se la configurazione non è valida.

Le classi vengono risolte dinamicamente dai moduli adapters.input e adapters.output
usando getattr(), eliminando la necessità di un registry esplicito.
"""

import logging
from queue import PriorityQueue, Queue

from .ports import InputPort, OutputPort

logger = logging.getLogger(__name__)


class AdapterFactory:
    """
    Factory per creare adapter Input/Output da configurazione.
    
    Risolve le classi dinamicamente dai moduli importati,
    senza bisogno di registrazione esplicita.
    """
    
    @classmethod
    def create_input_adapter(
        cls,
        class_name: str,
        config: dict,
        input_queue: PriorityQueue,
        interrupt_queue: Queue
    ) -> InputPort:
        """
        Crea un input adapter dalla configurazione.
        
        Args:
            class_name: Nome della classe (es: "MockVoiceInput")
            config: Configurazione specifica dell'adapter
            input_queue: Coda centralizzata per gli eventi
        
        Returns:
            Istanza di InputPort
            
        Raises:
            ValueError: Se la classe non esiste nel modulo
            RuntimeError: Se la creazione fallisce
        """
        try:
            # Importa il modulo degli input adapter
            import adapters.input as input_module
            
            # Ottieni la classe dal modulo usando getattr
            if not hasattr(input_module, class_name):
                available = ', '.join(input_module.__all__)
                logger.error(f"❌ Unknown input class: '{class_name}'")
                logger.info(f"Available classes: {available}")
                raise ValueError(
                    f"Unknown input adapter class '{class_name}'. "
                    f"Available: {available}"
                )
            
            adapter_class = getattr(input_module, class_name)
            
            # Verifica che estenda InputPort
            if not issubclass(adapter_class, InputPort):
                raise ValueError(
                    f"{class_name} must extend InputPort"
                )
            
            # Crea istanza
            adapter = adapter_class(
                name=class_name,
                config=config,
                input_queue=input_queue,
                interrupt_queue=interrupt_queue
            )
            
            logger.info(f"✅ Created input adapter: {adapter.name}")
            return adapter
            
        except ValueError:
            raise
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
    ) -> OutputPort:
        """
        Crea un output adapter dalla configurazione.
        
        Args:
            class_name: Nome della classe (es: "MockVoiceOutput")
            config: Configurazione specifica dell'adapter (include queue_maxsize)
        
        Returns:
            Istanza di OutputPort
            
        Raises:
            ValueError: Se la classe non esiste nel modulo
            RuntimeError: Se la creazione fallisce
        """
        try:
            # Importa il modulo degli output adapter
            import adapters.output as output_module
            
            # Ottieni la classe dal modulo usando getattr
            if not hasattr(output_module, class_name):
                available = ', '.join(output_module.__all__)
                logger.error(f"❌ Unknown output class: '{class_name}'")
                logger.info(f"Available classes: {available}")
                raise ValueError(
                    f"Unknown output adapter class '{class_name}'. "
                    f"Available: {available}"
                )
            
            adapter_class = getattr(output_module, class_name)
            
            # Verifica che estenda OutputPort
            if not issubclass(adapter_class, OutputPort):
                raise ValueError(
                    f"{class_name} must extend OutputPort"
                )
            
            # Crea istanza
            adapter = adapter_class(
                name=class_name,
                config=config
            )
            
            logger.info(f"✅ Created output adapter: {adapter.name}")
            return adapter
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(
                f"❌ Failed to create output adapter '{class_name}': {e}",
                exc_info=True
            )
            raise RuntimeError(
                f"Output adapter creation failed: {class_name}"
            ) from e
    
    @classmethod
    def get_available_classes(cls) -> dict:
        """
        Ritorna tutte le classi disponibili nei moduli.
        Utile per debugging e validazione.
        """
        import adapters.input as input_module
        import adapters.output as output_module
        
        return {
            'input': list(input_module.__all__),
            'output': list(output_module.__all__)
        }
