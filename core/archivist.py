from google import genai
from google.genai import types
import logging
import json

from infrastructure.memory_store import MemoryStore

logger = logging.getLogger(__name__)

class BuddyArchivist:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
             raise RuntimeError("BuddyArchivist not initialized. Call initialize() first.")
        return cls._instance

    @classmethod
    def initialize(cls, api_key: str, config: dict):
        if cls._instance is not None:
             return cls._instance
        cls._instance = cls(api_key, config)
        return cls._instance

    def __init__(self, api_key: str, config: dict):
        """
        Args:
            api_key: Google API key
            config: Configurazione archivist da YAML
        """
        if BuddyArchivist._instance is not None and BuddyArchivist._instance != self:
             raise RuntimeError("Use BuddyArchivist.get_instance()")

        self.config = config
        self.client = genai.Client(api_key=api_key)
        self.model_id = self.config["model_id"]

    def distill_and_save(self):
        """Distilla conversazioni non processate e salva in memoria permanente, una sessione alla volta"""
        
        # Inizializza database (singleton)
        self.memory_store = MemoryStore.get_instance()
        
        # Recupera le sessioni non archiviate
        sessions = self.memory_store.get_unarchived_sessions()
        if not sessions:
            logger.info("Nessuna sessione non processata trovata per la distillazione.")
            return

        logger.info(f"Trovate {len(sessions)} sessioni da archiviare")
        
        # Processa una sessione alla volta
        for session_id in sessions:
            logger.info(f"📦 Archiviazione sessione: {session_id}")
            
            # Recupera i log della sessione specifica
            logs = self.memory_store.get_unprocessed_history_by_session(session_id)
            if not logs:
                logger.warning(f"Nessun log trovato per sessione {session_id}")
                continue

            # Formatta la conversazione come unico blocco di testo
            formatted_logs = "\n".join([f"{role}: {text}" for _, role, text in logs])
            
            try:
                # Chiamata pulita: istruzioni nel sistema, dati nel contenuto
                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=f"Analizza questa conversazione:\n{formatted_logs}",
                    config=types.GenerateContentConfig(
                        system_instruction=self.config["system_instruction"],
                        response_mime_type="application/json",
                        temperature=self.config["temperature"]
                    )
                )

                # Fail-fast: response.text must be present
                if not response.text:
                    raise ValueError("Empty response from LLM")
                
                nuovi_ricordi = json.loads(response.text)
                
                if nuovi_ricordi:
                    logger.info(f"Estratti {len(nuovi_ricordi)} nuovi ricordi dalla sessione {session_id}")
                    for r in nuovi_ricordi:
                        if 'fatto' not in r:
                            logger.warning(f"❌ Ricordo senza 'fatto': {r}")
                            continue
                        
                        logger.debug(r)
                        # Uso del nuovo metodo per ChromaDB
                        self.memory_store.add_permanent_memory(
                            fact=r['fatto'],  # Required
                            category=r.get('categoria', 'generale'),  # Default ok
                            notes="", # Note opzionali
                            importance=r.get('importanza', 1)
                        )
                
                # Segna come processati SOLO i log di questa sessione
                ids = [log[0] for log in logs]
                self.memory_store.mark_as_processed(ids)
                logger.info(f"✅ Sessione {session_id}: {len(nuovi_ricordi)} ricordi salvati")

            except Exception as e:
                logger.error(f"❌ Errore durante la distillazione della sessione {session_id}: {e}")
                # Continua con la prossima sessione senza bloccare tutto