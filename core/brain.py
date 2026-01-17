"""
Buddy Brain - Logica di business pura
Zero dipendenze da I/O, hardware, code.
"""

import logging
import time
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
        
        # Polling per archivist (default: 30 secondi)
        self.archivist_interval = config.get("archivist_interval", 30.0)
        self.last_archivist_time = time.time()
        
        # Inizializza sessione chat
        self._init_chat_session()
        
        logger.info(f"🧠 BuddyBrain initialized (model: {self.model_id}, archivist_interval: {self.archivist_interval}s)")
    
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
            
        except (ValueError, TypeError) as e:
            # Configuration errors - fail fast
            logger.error(f"❌ Invalid chat configuration: {e}", exc_info=True)
            raise RuntimeError(f"Failed to initialize chat session: {e}") from e
        except Exception as e:
            # Network/API errors - critical but allow retry
            logger.error(f"❌ Failed to initialize chat session: {e}", exc_info=True)
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
            # Gestione per tipo di evento
            if input_event.type == EventType.DIRECT_OUTPUT:
                # Bypass Brain: unwrap l'evento interno e inoltralo direttamente
                output_events.extend(self._handle_direct_output(input_event))
            
            elif input_event.type == EventType.USER_SPEECH:
                output_events.extend(self._handle_user_input(input_event))
            
            elif input_event.type.name.startswith("SENSOR_"):
                output_events.extend(self._handle_sensor_input(input_event))
            
            elif input_event.type == EventType.SHUTDOWN:
                output_events.extend(self._handle_shutdown(input_event))
            
            else:
                logger.warning(f"Unhandled event type: {input_event.type}")
            
            # Controllo polling archivist (dopo ogni evento)
            output_events.extend(self._check_archivist_trigger())
        
        except KeyboardInterrupt:
            logger.info("Brain interrupted by user")
            raise
        except Exception as e:
            logger.error(f"Brain processing error for event {input_event.type}: {e}", exc_info=True)
            # Non propaghiamo per non bloccare il sistema, ma loggiamo tutto
        
        return output_events
    
    def _handle_direct_output(self, event: Event) -> List[Event]:
        """
        Gestisce DIRECT_OUTPUT: unwrap l'evento interno e inoltralo.
        Utile per:
        - Test hardware
        - Comandi diretti da API/console
        - Bypass della logica LLM
        - Automazioni hardware
        
        Il content deve essere un Event di tipo OUTPUT.
        """
        try:
            inner_event = event.content
            
            # Verifica che sia un Event valido
            if not isinstance(inner_event, Event):
                logger.error(
                    f"DIRECT_OUTPUT content must be an Event, got {type(inner_event)}"
                )
                return []
            
            # Verifica che sia un evento di output (non input)
            if inner_event.type in [EventType.USER_SPEECH, EventType.DIRECT_OUTPUT] or \
               inner_event.type.name.startswith("SENSOR_"):
                logger.warning(
                    f"DIRECT_OUTPUT should contain output events, got {inner_event.type}"
                )
                return []
            
            logger.info(
                f"🎯 Direct output bypass: {inner_event.type.value} "
                f"(content: {str(inner_event.content)[:50]})"
            )
            
            # Inoltra direttamente l'evento interno
            return [inner_event]
            
        except Exception as e:
            logger.error(f"Error unwrapping DIRECT_OUTPUT: {e}", exc_info=True)
            return []
    
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
        
        return output_events
    
    def _handle_sensor_input(self, event: Event) -> List[Event]:
        """Gestisce eventi dai sensori"""
        output_events = []
        
        # Logica proattiva (esempio)
        if event.type == EventType.SENSOR_PRESENCE:
            if event.content is True:
                # Presenza rilevata - usa energy levels per valutare qualità
                metadata = event.metadata or {}
                mov_energy = metadata.get('mov_energy', 0)
                static_energy = metadata.get('static_energy', 0)
                distance = metadata.get('distance', 0)
                
                # Rilevamento forte = persona vicina
                if mov_energy > 60 or static_energy > 60:
                    logger.info(f"👤 Presenza forte rilevata: dist={distance}cm, "
                               f"mov_energy={mov_energy}, static_energy={static_energy}")
                # Rilevamento debole = potrebbe essere rumore
                elif mov_energy < 20 and static_energy < 20:
                    logger.debug("👻 Presenza debole (possibile falso positivo)")
                else:
                    logger.debug(f"👤 Presenza rilevata: dist={distance}cm")
        
        elif event.type == EventType.SENSOR_TEMPERATURE:
            # Ora abbiamo sia temperatura che umidità nel metadata
            temp = float(event.content)
            humidity = event.metadata.get('humidity') if event.metadata else None
            
            if temp > 30:
                logger.debug(f"🌡️  Temperatura alta: {temp}°C (Umidità: {humidity}%)")
            
            # Esempio: logica combinata temperatura + umidità
            if temp > 28 and humidity and humidity > 70:
                logger.debug(f"🥵 Clima afoso rilevato: {temp}°C, {humidity}%")
        
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
        
        return output_events
    
    def _generate_response(self, user_text: str) -> str:
        """
        Genera risposta usando LLM.
        Logica isolata per facilitare testing/mocking.
        """
        if not self.chat_session:
            logger.error("Chat session not available - cannot generate response")
            return "Mi dispiace, non sono momentaneamente disponibile."
        
        try:
            response = self.chat_session.send_message(user_text)
            
            # Log grounding metadata se disponibile
            if response.candidates[0].grounding_metadata:
                logger.debug("Google Search utilizzata per questa risposta")
            
            return response.text
            
        except (ValueError, TypeError) as e:
            # Input/configuration errors - log and return graceful message
            logger.error(f"Invalid input for LLM: {e}", exc_info=True)
            return "Mi dispiace, non ho capito la richiesta."
        except Exception as e:
            # Network/API errors - log with full trace
            logger.error(f"LLM API error: {e}", exc_info=True)
            return "Mi dispiace, ho avuto un problema tecnico."
    
    def reset_session(self) -> None:
        """Reset della sessione chat (utile per testing)"""
        logger.info("Resetting chat session...")
        self._init_chat_session()
    
    def _check_archivist_trigger(self) -> List[Event]:
        """
        Controlla se è il momento di triggerare la distillazione memoria.
        Chiamato dopo ogni evento processato.
        
        Returns:
            Lista contenente evento DISTILL_MEMORY se necessario
        """
        current_time = time.time()
        elapsed = current_time - self.last_archivist_time
        
        if elapsed >= self.archivist_interval:
            logger.debug(f"⏰ Archivist trigger (elapsed: {elapsed:.1f}s)")
            self.last_archivist_time = current_time
            
            return [create_output_event(
                EventType.DISTILL_MEMORY,
                None,
                priority=EventPriority.LOW,
                metadata={"elapsed_seconds": elapsed}
            )]
        
        return []
