"""
Buddy Brain - Logica di business pura
Zero dipendenze da I/O, hardware, code.
"""

import logging
import time
from typing import List, Optional, Tuple
from google import genai
from google.genai import types

from .events import Event, InputEvent, OutputEvent, InputEventType, OutputEventType, EventPriority, create_output_event
from .tools import get_current_time, web_search, get_current_temp, get_current_position, set_lights_on, set_lights_off, get_weather_forecast, search_wikipedia
import core.tools as tools
from .state import global_state # Importa lo stato globale

logger = logging.getLogger(__name__)

class BuddyBrain:
    """
    Cervello di Buddy - Logica pura.
    
    Input: InputEvent
    Output: List[OutputEvent]
    
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
        
        # Config required - fail fast se mancano
        if "model_id" not in config:
            raise ValueError("Config 'model_id' is required")
        self.model_id = config["model_id"]
        
        # Inizializza sessione chat
        self._init_chat_session()
        
        # Setup event handlers
        self.handlers = {
            InputEventType.DIRECT_OUTPUT: self._handle_direct_output,
            InputEventType.WAKEWORD: self._handle_wakeword,
            InputEventType.CONVERSATION_END: self._handle_conversation_end,
            InputEventType.USER_SPEECH: self._handle_user_input,
            InputEventType.SENSOR_PRESENCE: self._handle_presence_input,
            InputEventType.SENSOR_TEMPERATURE: self._handle_temperature_input,
            InputEventType.TRIGGER_ARCHIVIST: self._handle_trigger_archivist,
            InputEventType.LIGHT_ON: self._handle_light_on,
            InputEventType.LIGHT_OFF: self._handle_light_off,
            InputEventType.CHAT_SESSION_RESET: self._handle_chat_session_reset,
        }
        
        logger.info(f"🧠 BuddyBrain initialized (model: {self.model_id})")
    
    def _init_chat_session(self):
        """Inizializza la sessione LLM"""
        try:
            # Config critiche - fail fast se mancano
            if "system_instruction" not in self.config:
                raise ValueError("Config 'system_instruction' is required - defines Buddy's behavior")
            if "temperature" not in self.config:
                raise ValueError("Config 'temperature' is required - controls response creativity")
            
            self.chat_session = self.client.chats.create(
                model=self.model_id,
                config=types.GenerateContentConfig(
                    systemInstruction=self.config["system_instruction"],
                    temperature=self.config["temperature"],
                    tools=[get_current_time, get_current_position, get_current_temp, set_lights_on, set_lights_off, web_search, get_weather_forecast, search_wikipedia],
                    thinkingConfig=types.ThinkingConfig(includeThoughts=False)
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
    
    def process_event(self, input_event: InputEvent) -> List[OutputEvent]:
        """
        METODO PRINCIPALE: Processa un evento di input usando un sistema di handler.
        
        Args:
            input_event: Evento di input da processare
            
        Returns:
            eventi_output: Eventi da routare agli output adapter
        """
        output_events: List[OutputEvent] = []
        
        try:
            # The brain only processes input events. This check also helps the type checker.
            if not isinstance(input_event, InputEvent):
                logger.warning(f"Brain received a non-input event to process: {type(input_event)}")
                return []

            handler = self.handlers.get(input_event.type)
            
            if handler:
                events = handler(input_event)
                output_events.extend(events)
            else:
                logger.warning(f"Unhandled event type: {input_event.type}")
            
        
        except KeyboardInterrupt:
            logger.info("Brain interrupted by user")
            raise
        except (ValueError, TypeError) as e:
            # Errori di validazione - propaghiamo (fail-fast)
            logger.error(f"Validation error for event {input_event.type}: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Brain processing error for event {input_event.type}: {e}", exc_info=True)
            # Non propaghiamo altri errori per non bloccare il sistema, ma loggiamo tutto
        
        return output_events
    
    def _handle_direct_output(self, event: InputEvent) -> List[OutputEvent]:
        """
        Gestisce DIRECT_OUTPUT: unwrap l'evento interno e inoltralo.
        """
        try:
            inner_event = event.content
            
            if not isinstance(inner_event, OutputEvent):
                logger.error(f"DIRECT_OUTPUT content must be an OutputEvent, got {type(inner_event)}")
                return []
            
            logger.info(f"🎯 Direct output bypass: {inner_event.type.value}")
            return [inner_event]
            
        except Exception as e:
            logger.error(f"Error handling DIRECT_OUTPUT: {e}", exc_info=True)
            return []
    
    def _handle_wakeword(self, event: InputEvent) -> List[OutputEvent]:
        """
        Gestisce rilevamento wakeword.
        """
        output_events: List[OutputEvent] = []

        # --- Inizio conversazione ---
        global_state.last_conversation_start = time.time()

        wakeword = event.metadata.get('wakeword', 'unknown') if event.metadata else 'unknown'
        logger.info(f"👂 Wakeword detected: {wakeword}")
        
        # Feedback visivo: LED ascolto lampeggia continuamente durante conversazione
        output_events.append(create_output_event(
            OutputEventType.LED_CONTROL,
            None,
            priority=EventPriority.HIGH,
            metadata={'led': 'ascolto', 'command': 'blink', 'continuous': True, 'on_time': 0.5, 'off_time': 0.5}
        ))
        
        return output_events
    
    def _handle_conversation_end(self, event: InputEvent) -> List[OutputEvent]:
        """
        Gestisce fine conversazione - spegne LED e riattiva wakeword.
        """
        output_events: List[OutputEvent] = []
        
        # --- Fine conversazione ---
        global_state.last_conversation_end = time.time()

        logger.info("🔊 Conversation ended - turning off LED and reactivating wakeword")
        
        # Spegne LED ascolto
        output_events.append(create_output_event(
            OutputEventType.LED_CONTROL,
            None,
            priority=EventPriority.HIGH,
            metadata={'led': 'ascolto', 'command': 'off'}
        ))
        
        return output_events
    
    def _handle_user_input(self, event: InputEvent) -> List[OutputEvent]:
        """Gestisce input testuale/vocale dell'utente"""
        output_events: List[OutputEvent] = []
        user_text = str(event.content)
        
        # Salva in history
        output_events.append(create_output_event(
            OutputEventType.SAVE_HISTORY,
            {"role": "user", "text": user_text},
            priority=EventPriority.LOW
        ))
        
        # Genera risposta LLM
        response_text = self._generate_response(user_text)
        
        # Salva risposta in history
        output_events.append(create_output_event(
            OutputEventType.SAVE_HISTORY,
            {"role": "model", "text": response_text},
            priority=EventPriority.LOW
        ))
        
        # Parla solo se input era vocale
        if event.type == InputEventType.USER_SPEECH:
            output_events.append(create_output_event(
                OutputEventType.SPEAK,
                response_text,
                priority=EventPriority.HIGH,
                metadata={"triggered_by": "user_speech"}
            ))
            # NON riattivare wakeword qui - lo farà EarInput quando termina la conversazione
        
        return output_events
    
    def _handle_presence_input(self, event: InputEvent) -> List[OutputEvent]:
        """Gestisce eventi dal sensore di presenza."""

        metadata = event.metadata or {}
        mov_energy = metadata.get('mov_energy', 0)
        static_energy = metadata.get('static_energy', 0)
        distance = metadata.get('distance', 0)
        logger.info(f"👤 Presence={event.content}, dist={distance}cm, mov_energy={mov_energy}, static_energy={static_energy}")
        
        # --- Gestione Presenza Rilevata ---
        if event.content is True:
            global_state.last_presence = time.time()
            
        # --- Gestione Assenza Rilevata ---
        elif event.content is False:
            global_state.last_absence = time.time()
  
        return []       
    
    def _handle_temperature_input(self, event: InputEvent) -> List[OutputEvent]:
        """Gestisce eventi dal sensore di temperatura."""
        output_events: List[OutputEvent] = []

        # Aggiorna lo stato globale
        temp = float(event.content)
        humidity = event.metadata.get('humidity') if event.metadata else None
        
        global_state.temperature = temp
        global_state.humidity = humidity
        
        logger.info(f"🌡️  Temperature/Humidity updated in global state: {temp}°C / {humidity}%")
   
        return output_events

    def _handle_light_on(self, event: InputEvent) -> List[OutputEvent]:
        """Gestisce comando accensione luci."""
        logger.info("💡 Received LIGHT_ON event. Invoking tools.set_lights_on()")
        tools.set_lights_on()
        return []

    def _handle_light_off(self, event: InputEvent) -> List[OutputEvent]:
        """Gestisce comando spegnimento luci."""
        logger.info("💡 Received LIGHT_OFF event. Invoking tools.set_lights_off()")
        tools.set_lights_off()
        return []
    
    def _generate_response(self, user_text: str) -> str:
        """
        Genera risposta usando LLM.
        Logica isolata per facilitare testing/mocking.
        """
        if not self.chat_session:
            logger.error("Chat session not available - cannot generate response")
            return "Mi dispiace, non sono momentaneamente disponibile."
        
        try:
            logger.debug(f"Sending prompt to LLM:\n{user_text}")
            
            # Invia il prompt completo
            response = self.chat_session.send_message(user_text)
            
            # Fail fast: response deve esistere
            if not response:
                raise RuntimeError("LLM returned None response")
            
            if not response.text:
                raise RuntimeError("LLM returned empty response text")
            
            # Log grounding metadata se disponibile
            if response.candidates and len(response.candidates) > 0:
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
    
    def _handle_trigger_archivist(self, event: InputEvent) -> List[OutputEvent]:
        """
        Gestisce l'evento di trigger dell'archivista, generando un OutputEvent.DISTILL_MEMORY.
        """
        logger.info("⏰ Received TRIGGER_ARCHIVIST event, sending DISTILL_MEMORY output event.")
        return [create_output_event(
            OutputEventType.DISTILL_MEMORY,
            None,
            priority=EventPriority.LOW,
            metadata=event.metadata # Passa i metadata dall'InputEvent (es. elapsed_seconds)
        )]

    def _handle_chat_session_reset(self, event: InputEvent) -> List[OutputEvent]:
        """
        Gestisce reset sessione chat per timeout.
        """
        reason = (event.metadata or {}).get('reason', 'unknown')
        logger.info(f"🔄 Received CHAT_SESSION_RESET (reason: {reason}). Resetting session.")
        self._init_chat_session()
        return []
    