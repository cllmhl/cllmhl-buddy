from google import genai
from google.genai import types
import logging

class BuddyBrain:
    def __init__(self, api_key: str):
        # La nuova libreria usa il concetto di Client
        self.client = genai.Client(api_key=api_key)
        
        self.system_instruction = """
        Il tuo nome è Buddy. Sei un'entità digitale unica che vive su un Raspberry Pi 5.
        CARATTERE: Sei curioso, osservatore e ironico. Non sei un servitore, ma un compagno tecnologico.
        MEMORIA: Hai accesso a un database dei ricordi. Se l'utente cita fatti passati, sii pronto a collegarli.
        CONTESTO FISICO: Ti trovi in una casa, senti tramite un Jabra 410 e vedi tramite un radar LD2410C.
        REGOLE: Risposte brevi (massimo 2-3 frasi), tono colloquiale e mai troppo formale.
        """
        
        # Inizializziamo la sessione di chat con la configurazione corretta
        self.chat_session = self.client.chats.create(
            model='gemini-2.5-flash-lite',
            config=types.GenerateContentConfig(
                system_instruction=self.system_instruction
            )
        )

    def respond(self, user_text: str) -> str:
        try:
            # La chiamata ora è leggermente più pulita
            response = self.chat_session.send_message(user_text)
            return response.text
        except Exception as e:
            logging.error(f"Errore API Gemini (Nuova Lib): {e}")
            return f"Errore API Gemini: {e}"