import google.generativeai as genai
import os
import logging

class BuddyBrain:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        
        self.system_instruction = """
        Il tuo nome è Buddy. Sei un'entità digitale unica che vive su un Raspberry Pi 5.
        CARATTERE: Sei curioso, osservatore e ironico. Non sei un servitore, ma un compagno tecnologico.
        MEMORIA: Hai accesso a un database dei ricordi. Se l'utente cita fatti passati, sii pronto a collegarli.
        CONTESTO FISICO: Ti trovi in una casa, senti tramite un Jabra 410 e vedi tramite un radar LD2410C.
        REGOLE: Risposte brevi (massimo 2-3 frasi), tono colloquiale e mai troppo formale.
        """
        
        self.model = genai.GenerativeModel(
            model_name='models/gemini-2.5-flash-lite',
            system_instruction=self.system_instruction
        )
        self.chat_session = self.model.start_chat(history=[])

    def respond(self, user_text: str) -> str:
        try:
            response = self.chat_session.send_message(user_text)
            return response.text
        except Exception as e:
            logging.error(f"Errore API Gemini: {e}")
            return f"Errore API Gemini: {e}"