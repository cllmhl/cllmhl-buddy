from google import genai
from google.genai import types
import logging
import json
import os

class BuddyBrain:
    def __init__(self, api_key: str):
        # Carica configurazione
        with open("buddy_config.json", "r") as f:
            self.config = json.load(f)["brain"]
            
        self.client = genai.Client(api_key=api_key)
        self.model_id = self.config["model_id"]
        
        # Inizializza sessione con parametri centralizzati
        self.chat_session = self.client.chats.create(
            model=self.model_id,
            config=types.GenerateContentConfig(
                system_instruction=self.config["system_instruction"],
                temperature=self.config.get("temperature", 0.7)
            )
        )

    def respond(self, user_text: str) -> str:
        try:
            response = self.chat_session.send_message(user_text)
            return response.text
        except Exception as e:
            logging.error(f"Errore Brain: {e}")
            return f"Errore neurale: {e}"