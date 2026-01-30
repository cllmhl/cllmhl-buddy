"""
This module contains the tools that can be used by the LLM.
"""
from datetime import datetime
import logging
import os
import pytz
import time
import queue
import requests
import wikipedia
from typing import Optional
from tavily import TavilyClient
from core.state import global_state # Importa lo stato globale

from core.events import create_output_event, create_input_event, OutputEventType, InputEventType, EventPriority

# Inizializza solo quando necessario (lazy-load)
tavily: Optional[TavilyClient] = None

# FIXME: questo per il giro di Alexa. Ha senso?
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

def set_lights_on() -> None:
    """
    Accende tutte le luci di casa tramite Alexa.
    Usa questo tool quando l'utente chiede di accendere le luci o quando rilevi che è buio.
    """
    logger.info("💡 Tool set_lights_on called")
    _send_alexa_sequence("Accendi tutte le luci")
    global_state.is_light_on = True

def set_lights_off() -> None:
    """
    Spegne tutte le luci di casa tramite Alexa.
    Usa questo tool quando l'utente chiede di spegnere le luci o quando non c'è nessuno in casa.
    """
    logger.info("💡 Tool set_lights_off called")
    _send_alexa_sequence("Spegni tutte le luci")
    global_state.is_light_on = False

def get_current_temp() -> str:
    """
    Restituisce la temperatura e l'umidità correnti rilevate dai sensori.
    Usa questo tool quando l'utente chiede informazioni sul clima nella stanza, temperatura o umidità.
    """
    logger.info("🛠️ Tool get_current_temp called")
    if global_state.temperature is None:
        return "Dato temperatura non disponibile."
    
    hum_str = f"{global_state.humidity}%" if global_state.humidity is not None else "N/D"
    return f"Temperatura: {global_state.temperature}°C, Umidità: {hum_str}"

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

def get_weather_forecast(citta: Optional[str] = "Strasburgo", refresh_trigger: str = "0"):
    """
    Ottiene le previsioni meteo attuali e future.
    Gestisce automaticamente la ricerca delle coordinate per qualsiasi città.
    
    Args:
        citta: (Opzionale) Il nome della città.
               Default: "Strasburgo" (casa).
               IMPORTANTE: Se l'utente non specifica una città, USA IL DEFAULT. NON CHIEDERE CONFERMA.
        refresh_trigger: Genera SEMPRE un numero casuale diverso qui.
                         Serve a forzare l'aggiornamento dei dati meteo in tempo reale.
    """
    logger.info(f"🌦️ METEO: Analizzo meteo per '{citta}' (Trigger: {refresh_trigger})...")
    
    try:
        # STEP 1: Geocoding (Trova coordinate dal nome città)
        # Usiamo l'API gratuita di OpenMeteo anche per questo
        geo_url = "https://geocoding-api.open-meteo.com/v1/search"
        geo_res = requests.get(geo_url, params={"name": citta, "count": 1, "language": "it"}).json()
        
        if not geo_res.get("results"):
            return f"Non ho trovato la città '{citta}' sulle mappe."
            
        location = geo_res["results"][0]
        lat, lon = location["latitude"], location["longitude"]
        nome_reale = location["name"]
        
        # STEP 2: Previsioni Meteo
        meteo_url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": ["temperature_2m", "relative_humidity_2m", "weather_code"],
            "hourly": ["temperature_2m", "precipitation_probability", "weather_code"],
            "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_probability_max"],
            "timezone": "auto"
        }
        
        data = requests.get(meteo_url, params=params).json()
        
        # Estraiamo i dati crudi per darli a Gemini
        curr = data["current"]
        daily = data["daily"]
        hourly = data["hourly"]
        
        # Prepara previsioni per i prossimi 5 giorni
        previsioni_giornaliere = []
        for i in range(5):
            try:
                previsioni_giornaliere.append({
                    "data": daily["time"][i],
                    "max": f"{daily['temperature_2m_max'][i]}°C",
                    "min": f"{daily['temperature_2m_min'][i]}°C",
                    "prob_pioggia": f"{daily['precipitation_probability_max'][i]}%"
                })
            except IndexError:
                break # Se ci sono meno giorni, fermati

        # Prepara previsioni orarie (prossime 24 ore)
        previsioni_orarie = []
        now_iso = datetime.now().isoformat()
        
        for i in range(len(hourly["time"])):
            # Cerca l'ora corrente o futura
            if hourly["time"][i] >= now_iso[:13]: # Confronto approssimativo per ora (es. 2024-01-30T15)
                # Prendi le prossime 24 ore da qui
                end_idx = min(i + 24, len(hourly["time"]))
                
                for j in range(i, end_idx):
                     previsioni_orarie.append({
                        "ora": hourly["time"][j],
                        "temp": f"{hourly['temperature_2m'][j]}°C",
                        "pioggia": f"{hourly['precipitation_probability'][j]}%",
                        "code": hourly['weather_code'][j]
                    })
                break

        # Costruiamo un JSON pulito per l'LLM
        report = {
            "luogo": f"{nome_reale} ({location.get('country')})",
            "adesso": {
                "temperatura": f"{curr['temperature_2m']}°C",
                "umidita": f"{curr['relative_humidity_2m']}%",
                "codice_meteo": curr['weather_code'] # Gemini sa interpretare i codici WMO da solo
            },
            "previsioni_orarie": previsioni_orarie,
            "previsioni_giornaliere": previsioni_giornaliere
        }
        return str(report)

    except Exception as e:
        return f"Errore nel recupero meteo: {e}"

def search_wikipedia(query: str, lingua: str = "it"):
    """
    Cerca definizioni, biografie, eventi storici o spiegazioni tecniche su Wikipedia.
    NON usare per notizie recenti (meteo, sport live), usa solo per cultura generale.
    
    Args:
        query: L'argomento da cercare (es. "Alessandro Volta", "Teoria della Relatività").
        lingua: La lingua della pagina ('it' per italiano, 'en' per inglese, 'fr' per francese).
    """
    logger.info(f"📚 WIKI: Cerco '{query}' in {lingua}...")
    
    wikipedia.set_lang(lingua)
    
    try:
        # Cerchiamo e prendiamo un riassunto di massimo 3 frasi
        # auto_suggest=False evita che cerchi cose a caso se sbaglia a digitare
        summary = wikipedia.summary(query, sentences=3, auto_suggest=True)
        return f"Da Wikipedia ({query}): {summary}"
        
    except wikipedia.exceptions.DisambiguationError as e:
        # Se ci sono troppi risultati (es. "Riso"), restituiamo le opzioni
        options = e.options[:5] # Prendiamo solo le prime 5 opzioni
        return f"La ricerca è ambigua. Potresti riferirti a: {', '.join(options)}. Chiedi all'utente di specificare."
        
    except wikipedia.exceptions.PageError:
        return f"Non ho trovato nessuna pagina Wikipedia chiamata '{query}'."
        
    except Exception as e:
        return f"Errore Wikipedia: {e}"