"""
This module contains the tools that can be used by the LLM.
"""
from datetime import datetime
import logging
import os
import pytz
from typing import Optional
from tavily import TavilyClient

# Inizializza solo quando necessario (lazy-load)
tavily: Optional[TavilyClient] = None

# Global state for temperature/humidity
CURRENT_TEMPERATURE: Optional[float] = None
CURRENT_HUMIDITY: Optional[float] = None

logger = logging.getLogger(__name__)

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
