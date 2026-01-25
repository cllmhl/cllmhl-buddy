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

logger = logging.getLogger(__name__)

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
