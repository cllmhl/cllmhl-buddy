"""
This module contains the tools that can be used by the LLM.
"""
from datetime import datetime
import logging
import pytz

logger = logging.getLogger(__name__)

def get_current_time() -> str:
    """
    Ritorna l'ora corrente in formato ISO 8601 per il fuso orario specificato (Europe/Rome).
    """
    logger.info("🛠️ Tool get_current_time called")
    time_zone = "Europe/Rome"
    now = datetime.now(pytz.timezone(time_zone))
    return now.isoformat()
