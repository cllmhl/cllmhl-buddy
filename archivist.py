from google import genai
from google.genai import types
import json
import logging

logger = logging.getLogger(__name__)

class BuddyArchivist:
    def __init__(self, api_key: str):
        # Carica la configurazione una volta all'avvio
        with open("buddy_config.json", "r") as f:
            self.config = json.load(f)["archivist"]
            
        self.client = genai.Client(api_key=api_key)
        self.model_id = self.config["model_id"]

    def distill_and_save(self, db):
        # Recupera i log non processati
        logs = db.get_unprocessed_history()
        if not logs:
            return

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
                    temperature=self.config.get("temperature", 0.1)
                )
            )

            nuovi_ricordi = json.loads(response.text)
            
            if nuovi_ricordi:
                logger.info(f"Estratti {len(nuovi_ricordi)} nuovi ricordi")
                for r in nuovi_ricordi:
                    logger.debug(r)
                    # Uso del nuovo metodo per ChromaDB
                    db.add_permanent_memory(
                        fact=r.get('fatto', ''),
                        category=r.get('categoria', 'generale'),
                        notes="", # Note opzionali
                        importance=r.get('importanza', 1)
                    )
            
            # Segna come processati
            ids = [log[0] for log in logs]
            db.mark_as_processed(ids)
            logger.info(f"{len(nuovi_ricordi)} ricordi salvati con successo.")

        except Exception as e:
            logger.error(f"Errore durante la distillazione: {e}")