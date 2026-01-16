"""
Buddy Brain - Logica di business pura
Zero dipendenze da I/O, hardware, code.
"""

import logging
from typing import List, Optional
from google import genai
from google.genai import types

from .events import Event, EventType, EventPriority, create_output_event

logger = logging.getLogger(__name__)


class BuddyBrain:
    """
    Cervello di Buddy - Logica pura.
    
    Input: Event di input
    Output: List[Event] di output
    
    NON SA NULLA DI:
    - Code
    - Adapter
    - Hardware
    - File system
    """
    
    def __init__(self, api_key: str, config: dict):
        """
        Args:
            api_key: Google AI API key
            config: Configurazione brain (model_id, system_instruction, etc)
        """
        self.config = config
        self.api_key = api_key
        
        # Client Google AI
        self.client = genai.Client(api_key=api_key)
        self.model_id = config.get("model_id", "gemini-2.0-flash-exp")
        
        # Inizializza sessione chat
        self._init_chat_session()
        
        logger.info(f"🧠 BuddyBrain initialized (model: {self.model_id})")
    
    def _init_chat_session(self):
        """Inizializza la sessione LLM"""
        try:
            self.chat_session = self.client.chats.create(
                model=self.model_id,
                config=types.GenerateContentConfig(
                    system_instruction=self.config.get(
                        "system_instruction",
                        "Sei Buddy, un assistente AI amichevole."
                    ),
                    temperature=self.config.get("temperature", 0.7),
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    thinking_config=types.ThinkingConfig(include_thoughts=False)
                )
            )
            logger.info("✅ Chat session initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize chat session: {e}")
            self.chat_session = None
    
    def process_event(self, input_event: Event) -> List[Event]:
        """
        METODO PRINCIPALE: Processa un evento di input.
        
        Args:
            input_event: Evento di input da processare
            
        Returns:
            Lista di eventi di output da eseguire
        """
        output_events = []
        
        try:
            # Log dell'input ricevuto
            output_events.append(create_output_event(
                EventType.LOG_INFO,
                f"Brain received: {input_event.type.value} from {input_event.source}",
                priority=EventPriority.LOW
            ))
            
            # Gestione per tipo di evento
            if input_event.type in [
                EventType.USER_SPEECH,
                EventType.PIPE_COMMAND
            ]:
                output_events.extend(self._handle_user_input(input_event))
            
            elif input_event.type.name.startswith("SENSOR_"):
                output_events.extend(self._handle_sensor_input(input_event))
            
            elif input_event.type == EventType.SHUTDOWN:
                output_events.extend(self._handle_shutdown(input_event))
            
            else:
                logger.warning(f"Unhandled event type: {input_event.type}")
        
        except Exception as e:
            logger.error(f"Brain processing error: {e}", exc_info=True)
            output_events.append(create_output_event(
                EventType.LOG_ERROR,
                f"Brain error: {str(e)}",
                priority=EventPriority.HIGH
            ))
        
        return output_events
    
    def _handle_user_input(self, event: Event) -> List[Event]:
        """Gestisce input testuale/vocale dell'utente"""
        output_events = []
        user_text = str(event.content)
        
        # Salva in history
        output_events.append(create_output_event(
            EventType.SAVE_HISTORY,
            {"role": "user", "text": user_text},
            priority=EventPriority.LOW
        ))
        
        # Genera risposta LLM
        response_text = self._generate_response(user_text)
        
        # Salva risposta in history
        output_events.append(create_output_event(
            EventType.SAVE_HISTORY,
            {"role": "model", "text": response_text},
            priority=EventPriority.LOW
        ))
        
        # Parla solo se input era vocale
        if event.type == EventType.USER_SPEECH:
            output_events.append(create_output_event(
                EventType.SPEAK,
                response_text,
                priority=EventPriority.HIGH,
                metadata={"triggered_by": "user_speech"}
            ))
        
        # Log della risposta
        output_events.append(create_output_event(
            EventType.LOG_INFO,
            f"Brain response: {response_text[:100]}...",
            priority=EventPriority.LOW
        ))
        
        return output_events
    
    def _handle_sensor_input(self, event: Event) -> List[Event]:
        """Gestisce eventi dai sensori"""
        output_events = []
        
        # Log del sensore
        output_events.append(create_output_event(
            EventType.LOG_INFO,
            f"Sensor {event.type.value}: {event.content}",
            priority=EventPriority.LOW
        ))
        
        # Logica proattiva (esempio)
        if event.type == EventType.SENSOR_PRESENCE:
            if event.content is True:
                # Presenza rilevata - potremmo fare qualcosa
                logger.debug("Presenza rilevata, nessuna azione per ora")
        
        elif event.type == EventType.SENSOR_TEMPERATURE:
            temp = float(event.content)
            if temp > 30:
                # Temperatura alta - Buddy potrebbe commentare
                logger.debug(f"Temperatura alta: {temp}°C")
        
        return output_events
    
    def _handle_shutdown(self, event: Event) -> List[Event]:
        """Gestisce comando di shutdown"""
        output_events = []
        
        # Se era vocale, saluta
        if event.source == "voice":
            output_events.append(create_output_event(
                EventType.SPEAK,
                "Mi sto spegnendo. A presto!",
                priority=EventPriority.CRITICAL
            ))
        
        output_events.append(create_output_event(
            EventType.LOG_INFO,
            "Shutdown requested",
            priority=EventPriority.HIGH
        ))
        
        return output_events
    
    def _generate_response(self, user_text: str) -> str:
        """
        Genera risposta usando LLM.
        Logica isolata per facilitare testing/mocking.
        """
        if not self.chat_session:
            return "Errore: Sessione LLM non disponibile."
        
        try:
            response = self.chat_session.send_message(user_text)
            
            # Log grounding metadata se disponibile
            if response.candidates[0].grounding_metadata:
                logger.debug("Google Search utilizzata per questa risposta")
            
            return response.text
            
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return f"Errore neurale: {str(e)}"
    
    def reset_session(self) -> None:
        """Reset della sessione chat (utile per testing)"""
        logger.info("Resetting chat session...")
        self._init_chat_session()
