from google import genai
from google.genai import types
import json
import logging

class BuddyArchivist:
    def __init__(self, api_key: str):
        # Inizializziamo il client con la nuova libreria
        self.client = genai.Client(api_key=api_key)
        self.model_id = 'models/gemini-2.5-flash' # Usiamo il Pro? non funziona e non capisco i limiti..

    def distill_and_save(self, db):
        """Prende i log dal database, li analizza e salva i ricordi."""
        logs = db.get_unprocessed_history()
        if not logs:
            return

        # Prepariamo la conversazione per il prompt
        formatted_logs = "\n".join([f"{role}: {text}" for _, role, text in logs])
        
        prompt = f"""
        Sei l'Archivista di Buddy. Il tuo compito è distillare la conversazione seguente in fatti memorabili.
        CONVERSAZIONE:
        {formatted_logs}

        REGOLE DI OUTPUT:
        1. Estrai solo informazioni personali, preferenze, progetti o scadenze dell'utente.
        2. Rispondi ESCLUSIVAMENTE con un array JSON.
        3. Ogni oggetto deve avere: "fatto", "categoria", "importanza" (1-5).
        4. Se non c'è nulla di utile, rispondi con [].
        """

        try:
            # Chiamata alla nuova API
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json" # Forza l'output in JSON
                )
            )

            # Parsing del risultato
            nuovi_ricordi = json.loads(response.text)

            # Salvataggio nel database
            if nuovi_ricordi:
                for r in nuovi_ricordi:
                    db.add_permanent_memory(
                        r.get('fatto'), 
                        r.get('categoria'), 
                        "", 
                        r.get('importanza', 1)
                    )
            
            # Segniamo i log come processati per non rileggerli
            ids = [log[0] for log in logs]
            db.mark_as_processed(ids)
            
            logging.info(f"Archivista: Processati {len(ids)} messaggi, estratti {len(nuovi_ricordi)} ricordi.")

        except Exception as e:
            logging.error(f"Errore durante l'archiviazione: {e}")
            print(f"\n[Errore Archivista] {e}")