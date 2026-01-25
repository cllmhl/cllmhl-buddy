"""
This module contains the tools that can be used by the LLM.
"""
from datetime import datetime
import logging
import os
import pytz
import time
import queue
from typing import Optional
from tavily import TavilyClient

from core.events import create_output_event, create_input_event, OutputEventType, InputEventType, EventPriority

# Inizializza solo quando necessario (lazy-load)
tavily: Optional[TavilyClient] = None

# Global state for temperature/humidity
CURRENT_TEMPERATURE: Optional[float] = None
CURRENT_HUMIDITY: Optional[float] = None

# Global event queue for side effects (DIRECT_OUTPUT)
_INPUT_QUEUE: Optional[queue.PriorityQueue] = None

logger = logging.getLogger(__name__)

def set_input_queue(q: queue.PriorityQueue):
    """
    Imposta la coda di input globale per permettere ai tool di inviare eventi.
    """
    global _INPUT_QUEUE
    _INPUT_QUEUE = q
    logger.info("✅ Tools: Input queue injected")

def _send_alexa_sequence(command: str) -> None:
    """
    Invia una sequenza di comandi Alexa (Wakeword + Command) alla input queue.
    """
    if _INPUT_QUEUE is None:
        logger.error("❌ Cannot send Alexa command: Input queue not set in tools")
        return

    # 1. Evento Wakeword "Alexa;"
    wakeword_event = create_output_event(
        OutputEventType.SPEAK,
        "Alexa; ",
        priority=EventPriority.HIGH,
        metadata={"triggered_by": "tool_alexa_wakeword"}
    )
    # Wrap in DIRECT_OUTPUT per iniettarlo nel sistema
    input_evt_1 = create_input_event(
        InputEventType.DIRECT_OUTPUT,
        wakeword_event,
        source="tools",
        priority=EventPriority.HIGH
    )
    _INPUT_QUEUE.put(input_evt_1)
    
    # Pausa per garantire sequenza corretta
    time.sleep(1.0)
    
    # 2. Evento Comando
    command_event = create_output_event(
        OutputEventType.SPEAK,
        command,
        priority=EventPriority.HIGH,
        metadata={"triggered_by": "tool_alexa_command"}
    )
    input_evt_2 = create_input_event(
        InputEventType.DIRECT_OUTPUT,
        command_event,
        source="tools",
        priority=EventPriority.HIGH
    )
    _INPUT_QUEUE.put(input_evt_2)

def set_lights_on() -> str:
    """
    Accende tutte le luci di casa tramite Alexa.
    Usa questo tool quando l'utente chiede di accendere le luci o quando rilevi che è buio.
    """
    logger.info("💡 Tool set_lights_on called")
    _send_alexa_sequence("Accendi tutte le luci")
    return "Sto accendendo le luci."

def set_lights_off() -> str:
    """
    Spegne tutte le luci di casa tramite Alexa.
    Usa questo tool quando l'utente chiede di spegnere le luci o quando non c'è nessuno in casa.
    """
    logger.info("💡 Tool set_lights_off called")
    _send_alexa_sequence("Spegni tutte le luci")
    return "Sto spegnendo le luci."

def set_current_temp(temp: float, humidity: Optional[float] = None):
    """
    Aggiorna la temperatura e umidità correnti (chiamato dal Brain).
    """
    global CURRENT_TEMPERATURE, CURRENT_HUMIDITY
    CURRENT_TEMPERATURE = temp
    CURRENT_HUMIDITY = humidity
    logger.debug(f"Tools state updated: T={temp}, H={humidity}")

def get_current_temp() -> str:
    """
    Restituisce la temperatura e l'umidità correnti rilevate dai sensori.
    Usa questo tool quando l'utente chiede informazioni sul clima nella stanza, temperatura o umidità.
    """
    global CURRENT_TEMPERATURE, CURRENT_HUMIDITY
    if CURRENT_TEMPERATURE is None:
        return "Dato temperatura non disponibile."
    
    hum_str = f"{CURRENT_HUMIDITY}%" if CURRENT_HUMIDITY is not None else "N/D"
    return f"Temperatura: {CURRENT_TEMPERATURE}°C, Umidità: {hum_str}"

def get_current_time() -> str:
    """
    Ritorna l'ora corrente in formato ISO 8601 per il fuso orario specificato (Europe/Rome).
    """
    logger.info("🛠️ Tool get_current_time called")
    time_zone = "Europe/Rome"
    now = datetime.now(pytz.timezone(time_zone))
    return now.isoformat()

def web_search(query: str):
    """Cerca sul web usando un motore ottimizzato per AI."""
    global tavily
    logger.info("🛠️ Tool web_search called")

    # Lazy initialization
    if tavily is None:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            logger.error("TAVILY_API_KEY not found in environment. Cannot perform web search.")
            return "Errore: Chiave API Tavily non configurata."
        
        tavily = TavilyClient(api_key=api_key)
        logger.info("🔑 Tavily client initialized using TAVILY_API_KEY from environment.")

    try:
        # search_depth="basic" è veloce, "advanced" è profondo
        response = tavily.search(query=query, search_depth="basic", max_results=3)
        
        # Tavily restituisce già un riassunto (content) perfetto per Gemini
        context = [r['content'] for r in response['results']]
        return "\n".join(context)
        
    except Exception as e:
        return f"Errore ricerca: {e}"

def get_current_position():
    """
    Restituisce la posizione geografica esatta (GPS) di Buddy (Casa).
    Usa questo tool quando l'utente chiede informazioni sulla posizione geografica di Buddy.
    """
    logger.info("🛠️ Tool get_current_position called")

    return {
        "latitude": 48.556880087844924, 
        "longitude": 7.746873007622421,
        "city": "Strasburgo",    # Opzionale, aiuta Gemini nel contesto
        "country": "Francia"
    }