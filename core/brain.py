"""
Buddy Brain - Logica di business pura
Zero dipendenze da I/O, hardware, code.
"""

import logging
import time
from typing import List, Optional, Tuple
from google import genai
from google.genai import types

from .events import Event, InputEventType, OutputEventType, EventPriority, create_output_event
from .commands import AdapterCommand

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
        
        # Config required - fail fast se mancano
        if "model_id" not in config:
            raise ValueError("Config 'model_id' is required")
        self.model_id = config["model_id"]
        
        if "archivist_interval" not in config:
            raise ValueError("Config 'archivist_interval' is required - controls memory distillation frequency")
        self.archivist_interval = config["archivist_interval"]
        self.last_archivist_time = time.time()
        
        # Timer per spegnimento luci
        self.presence_lost_timestamp: Optional[float] = None
        self.light_off_timeout: int = 180 # Secondi. TODO: Spostare in config.
        
        # Inizializza sessione chat
        self._init_chat_session()
        
        # Setup event handlers
        self.handlers = {
            InputEventType.DIRECT_OUTPUT: self._handle_direct_output,
            InputEventType.ADAPTER_COMMAND: self._handle_adapter_command,
            InputEventType.WAKEWORD: self._handle_wakeword,
            InputEventType.CONVERSATION_END: self._handle_conversation_end,
            InputEventType.USER_SPEECH: self._handle_user_input,
            InputEventType.SENSOR_PRESENCE: self._handle_sensor_input,
            InputEventType.SENSOR_TEMPERATURE: self._handle_sensor_input,
            InputEventType.SENSOR_HUMIDITY: self._handle_sensor_input,
            InputEventType.SENSOR_MOVEMENT: self._handle_sensor_input,
            InputEventType.SHUTDOWN: self._handle_shutdown,
        }
        
        logger.info(f"🧠 BuddyBrain initialized (model: {self.model_id}, archivist_interval: {self.archivist_interval}s)")
    
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
                    system_instruction=self.config["system_instruction"],
                    temperature=self.config["temperature"],
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
    
    def process_event(self, input_event: Event) -> Tuple[List[Event], List[AdapterCommand]]:
        """
        METODO PRINCIPALE: Processa un evento di input usando un sistema di handler.
        
        Args:
            input_event: Evento di input da processare
            
        Returns:
            Tuple di (eventi_output, comandi_adapter):
            - eventi_output: Eventi da routare agli output adapter
            - comandi_adapter: Comandi da broadcast a TUTTI gli adapter (sync)
        """
        output_events: List[Event] = []
        adapter_commands: List[AdapterCommand] = []
        
        try:
            # The brain only processes input events. This check also helps the type checker.
            if not isinstance(input_event.type, InputEventType):
                logger.warning(f"Brain received a non-input event to process: {input_event.type}")
                return [], []

            handler = self.handlers.get(input_event.type)
            
            if handler:
                events, commands = handler(input_event)
                output_events.extend(events)
                adapter_commands.extend(commands)
            else:
                logger.warning(f"Unhandled event type: {input_event.type}")
            
            # Controllo polling archivist (dopo ogni evento)
            output_events.extend(self._check_archivist_trigger())
            output_events.extend(self._check_light_off_timer())
        
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
        
        return output_events, adapter_commands
    
    def _handle_direct_output(self, event: Event) -> Tuple[List[Event], List[AdapterCommand]]:
        """
        Gestisce DIRECT_OUTPUT: unwrap l'evento interno e inoltralo.
        """
        try:
            inner_event = event.content
            
            if not isinstance(inner_event, Event):
                logger.error(f"DIRECT_OUTPUT content must be an Event, got {type(inner_event)}")
                return [], []
            
            if isinstance(inner_event.type, InputEventType):
                logger.warning(f"DIRECT_OUTPUT should contain output events, got {inner_event.type}")
                return [], []
            
            logger.info(f"🎯 Direct output bypass: {inner_event.type.value}")
            return [inner_event], []
            
        except Exception as e:
            logger.error(f"Error handling DIRECT_OUTPUT: {e}", exc_info=True)
            return [], []
    
    def _handle_adapter_command(self, event: Event) -> Tuple[List[Event], List[AdapterCommand]]:
        """
        Gestisce ADAPTER_COMMAND: converte il comando e lo invia agli adapter.
        """
        command_name = event.content
        
        if not isinstance(command_name, str):
            logger.error(f"ADAPTER_COMMAND content must be string, got {type(command_name)}")
            raise TypeError(f"Command name must be string, got {type(command_name)}")
        
        try:
            command = AdapterCommand(command_name)
            logger.info(f"🎛️  ADAPTER_COMMAND received: {command.value}")
            return [], [command]
        except ValueError:
            logger.error(f"❌ Invalid adapter command: {command_name}")
            available = ", ".join([c.value for c in AdapterCommand])
            raise ValueError(f"Unknown adapter command: {command_name}. Available: {available}")
    
    def _handle_wakeword(self, event: Event) -> Tuple[List[Event], List[AdapterCommand]]:
        """
        Gestisce rilevamento wakeword.
        """
        output_events = []
        commands = []
        
        wakeword = event.metadata.get('wakeword', 'unknown') if event.metadata else 'unknown'
        logger.info(f"👂 Wakeword detected: {wakeword}")
        
        # Feedback visivo: LED ascolto lampeggia continuamente durante conversazione
        output_events.append(create_output_event(
            OutputEventType.LED_CONTROL,
            None,
            priority=EventPriority.HIGH,
            metadata={'led': 'ascolto', 'command': 'blink', 'continuous': True, 'on_time': 0.5, 'off_time': 0.5}
        ))
        
        # STOP wakeword detection (evita loop)
        commands.append(AdapterCommand.WAKEWORD_LISTEN_STOP)
        
        # START voice input per catturare comando utente
        commands.append(AdapterCommand.VOICE_INPUT_START)
        
        return output_events, commands
    
    def _handle_conversation_end(self, event: Event) -> Tuple[List[Event], List[AdapterCommand]]:
        """
        Gestisce fine conversazione - spegne LED e riattiva wakeword.
        """
        output_events = []
        commands = []
        
        logger.info("🔊 Conversation ended - turning off LED and reactivating wakeword")
        
        # Spegne LED ascolto
        output_events.append(create_output_event(
            OutputEventType.LED_CONTROL,
            None,
            priority=EventPriority.HIGH,
            metadata={'led': 'ascolto', 'command': 'off'}
        ))
        
        # Riattiva detection wakeword
        commands.append(AdapterCommand.WAKEWORD_LISTEN_START)
        
        return output_events, commands
    
    def _handle_user_input(self, event: Event) -> Tuple[List[Event], List[AdapterCommand]]:
        """Gestisce input testuale/vocale dell'utente"""
        output_events = []
        commands = []
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
        
        return output_events, commands
    
    def _handle_sensor_input(self, event: Event) -> Tuple[List[Event], List[AdapterCommand]]:
        """Gestisce eventi dai sensori"""
        output_events: List[Event] = []
        
        # Logica proattiva (esempio)
        if event.type == InputEventType.SENSOR_PRESENCE:
            # --- Gestione Presenza Rilevata ---
            if event.content is True:
                # Se il timer di spegnimento era attivo, cancellalo e non fare altro
                if self.presence_lost_timestamp is not None:
                    logger.info("👤 Presence re-detected within timeout, cancelling light-off timer. Lights were never off.")
                    self.presence_lost_timestamp = None
                    return [], []
                
                # Altrimenti, questa è una nuova presenza, applica la logica normale
                metadata = event.metadata or {}
                mov_energy = metadata.get('mov_energy', 0)
                static_energy = metadata.get('static_energy', 0)
                distance = metadata.get('distance', 0)
                
                logger.info(f"👤 New presence detected: dist={distance}cm, mov_energy={mov_energy}, static_energy={static_energy}")

                current_hour = time.localtime().tm_hour
                if current_hour >= 18 or current_hour < 7:
                    logger.info("💡 Rilevata presenza in orario notturno, accendo le luci.")
                    self._send_alexa_command("Accendi tutte le luci", output_events)
                elif mov_energy < 20 and static_energy < 20:
                    logger.debug("👻 Presenza debole (possibile falso positivo)")
                else:
                    logger.debug(f"👤 Presenza rilevata: dist={distance}cm")

            # --- Gestione Assenza Rilevata ---
            elif event.content is False:
                # Avvia il timer di spegnimento solo se non è già partito
                if self.presence_lost_timestamp is None:
                    logger.info(f"👤 Absence detected, starting {self.light_off_timeout}s timer to turn off lights.")
                    self.presence_lost_timestamp = time.time()
                else:
                    logger.debug("👤 Absence confirmed, light-off timer already running.")
        
        elif event.type == InputEventType.SENSOR_TEMPERATURE:
            # Ora abbiamo sia temperatura che umidità nel metadata
            temp = float(event.content)
            humidity = event.metadata.get('humidity') if event.metadata else None
            
            if temp > 30:
                logger.debug(f"🌡️  Temperatura alta: {temp}°C (Umidità: {humidity}%)")
            
            # Esempio: logica combinata temperatura + umidità
            if temp > 28 and humidity and humidity > 70:
                logger.debug(f"🥵 Clima afoso rilevato: {temp}°C, {humidity}%")
        
        return output_events, []
    
    def _handle_shutdown(self, event: Event) -> Tuple[List[Event], List[AdapterCommand]]:
        """Gestisce comando di shutdown"""
        output_events = []
        
        # Se era vocale, saluta
        if event.source == "voice":
            output_events.append(create_output_event(
                OutputEventType.SPEAK,
                "Mi sto spegnendo. A presto!",
                priority=EventPriority.CRITICAL
            ))
        
        return output_events, []
    
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
    
    def _send_alexa_command(self, command: str, output_events: List[Event]):
        """
        Genera una sequenza di eventi SPEAK per pronunciare un comando Alexa.
        La pausa tra "Alexa" e il comando è gestita implicitamente dalla coda
        dell'adattatore vocale, che processa un evento alla volta.
        """
        logger.info(f"🎙️ Sending Alexa command: {command}")
        
        # Evento 1: Pronuncia "Alexa"
        output_events.append(create_output_event(
            OutputEventType.SPEAK,
            "Alexa; ",
            priority=EventPriority.HIGH,
            metadata={"triggered_by": "alexa_automation_wakeword"}
        ))
        
        time.sleep(1)
        
        # Evento 2: Pronuncia il comando
        output_events.append(create_output_event(
            OutputEventType.SPEAK,
            command,
            priority=EventPriority.HIGH,
            metadata={"triggered_by": "alexa_automation_command"}
        ))

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
                OutputEventType.DISTILL_MEMORY,
                None,
                priority=EventPriority.LOW,
                metadata={"elapsed_seconds": elapsed}
            )]
        
        return []
    
    def _check_light_off_timer(self) -> List[Event]:
        """
        Controlla se il timer di spegnimento luci è scaduto.
        Chiamato dopo ogni evento processato.
        """
        if self.presence_lost_timestamp is None:
            return []

        elapsed = time.time() - self.presence_lost_timestamp
        if elapsed >= self.light_off_timeout:
            logger.info(f"💡 Light-off timer expired after {elapsed:.1f}s. Turning off lights.")
            
            # Reset timer
            self.presence_lost_timestamp = None
            
            # Generate events to turn off lights
            output_events: List[Event] = []
            self._send_alexa_command("spegni tutte le luci", output_events)
            return output_events
            
        return []
