from google import genai
from google.genai import types
import json
import logging

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

        formatted_logs = "\n".join([f"{role}: {text}" for _, role, text in logs])
        
        # Costruiamo il prompt dinamicamente dalle regole nel JSON
        rules_str = "\n".join([f"- {rule}" for rule in self.config['output_rules']])
        
        prompt = f"""
        {self.config['prompt_header']}

        REGOLE DA SEGUIRE:
        {rules_str}

        CONVERSAZIONE DA ANALIZZARE:
        {formatted_logs}
        """

        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=self.config.get("temperature", 0.1)
                )
            )

            nuovi_ricordi = json.loads(response.text)
            
            if nuovi_ricordi:
                logging.info(f"Archivista: Estratti {len(nuovi_ricordi)} nuovi ricordi")
                for r in nuovi_ricordi:
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
            logging.info(f"Archivista: {len(nuovi_ricordi)} ricordi estratti con successo.")

        except Exception as e:
            logging.error(f"Errore Archivista durante la distillazione: {e}")