from logging.handlers import RotatingFileHandler
import os
import logging
from dotenv import load_dotenv
import threading
import queue
import time
import subprocess
from dataclasses import dataclass
import speech_recognition as sr
from gtts import gTTS

# Le tue classi esistenti
from database_buddy import BuddyDatabase
from brain import BuddyBrain
from archivist import BuddyArchivist

# --- CONFIGURAZIONE LOGGING ---
# I log vanno SOLO su file, niente output su console
handler = RotatingFileHandler('buddy_system.log', maxBytes=10*1024*1024, backupCount=1)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(threadName)s - %(message)s')
handler.setFormatter(formatter)

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

# --- DEFINIZIONE EVENTI ---
@dataclass
class BuddyEvent:
    source: str      # "terminal", "jabra", "sensor"
    content: str     # Il testo o il dato
    timestamp: float = 0.0

# Semaforo per evitare l'auto-ascolto
buddy_is_speaking = threading.Event()
# Coda centrale
event_queue = queue.Queue()

# --- ATTUATORI (OUTPUT) ---

def speak_text(text):
    """Genera audio TTS."""
    try:
        logger.debug(f"Inizio sintesi vocale: {text[:20]}...")
        buddy_is_speaking.set()
        
        tts = gTTS(text=text, lang='it')
        filename = "temp_response.mp3"
        tts.save(filename)
        
        logger.debug("Riproduzione audio avviata")
        subprocess.run(["mpg123", "-q", filename])
        
        if os.path.exists(filename):
            os.remove(filename)
        logger.debug("Riproduzione audio completata")
            
    except Exception as e:
        logger.error(f"Errore TTS: {e}")
    finally:
        buddy_is_speaking.clear()

# --- SENSORI (INPUT THREADS) ---

def keyboard_thread():
    """Ascolta il terminale."""
    logger.info("Thread tastiera avviato")
    while True:
        try:
            text = input() 
            if text:
                event = BuddyEvent(source="terminal", content=text, timestamp=time.time())
                event_queue.put(event)
        except EOFError:
            break

def jabra_thread():
    """Ascolta il microfono Jabra."""
    r = sr.Recognizer()
    logger.info("Thread Jabra avviato")
    
    while True:
        if buddy_is_speaking.is_set():
            time.sleep(0.1)
            continue

        try:
            with sr.Microphone() as source:
                # Timeout breve per non bloccare il thread per sempre se c'è silenzio
                try:
                    # logger.debug("Jabra in ascolto...") # Troppo verboso anche per il log?
                    audio = r.listen(source, timeout=1, phrase_time_limit=5)
                    text = r.recognize_google(audio, language="it-IT")
                    
                    if text:
                        logger.info(f"Jabra Input Rilevato: {text}")
                        event = BuddyEvent(source="jabra", content=text, timestamp=time.time())
                        event_queue.put(event)
                        
                except sr.WaitTimeoutError:
                    pass 
                except sr.UnknownValueError:
                    pass 
                    
        except Exception as e:
            logger.error(f"Errore critico Jabra: {e}")
            time.sleep(1)

# --- MAIN LOOP ---

def main():
    load_dotenv()
    
    # Inizializzazione
    try:
        db = BuddyDatabase()
        api_key = os.getenv("GOOGLE_API_KEY")
        buddy = BuddyBrain(api_key)
        archivist = BuddyArchivist(api_key=api_key)
        logger.info("Sottosistemi inizializzati correttamente")
    except Exception as e:
        print(f"Errore critico in avvio: {e}")
        return

    # Avvio Threads
    t_key = threading.Thread(target=keyboard_thread, daemon=True, name="KbdThread")
    t_key.start()

    # --- CONTROLLO HARDWARE AUDIO ---
    audio_enabled = False
    try:
        # Verifica se ci sono microfoni collegati
        mics = sr.Microphone.list_microphone_names()
        if mics:
            logger.info(f"Microfoni trovati: {mics}")
            t_jabra = threading.Thread(target=jabra_thread, daemon=True, name="JabraThread")
            t_jabra.start()
            audio_enabled = True
        else:
            logger.warning("Nessun microfono rilevato. JabraThread non avviato.")
    except Exception as e:
        logger.error(f"Impossibile verificare l'hardware audio: {e}")

    # Output visibile all'avvio
    msg_audio = "Attivo" if audio_enabled else "Non disponibile"
    print("\n--- Buddy OS Online ---")
    print(f"Audio: {msg_audio} | Log: buddy_system.log")
    print("\nTu > ", end="", flush=True)

    last_archive_time = time.time()

    try:
        while True:
            # 1. GESTIONE EVENTI
            if not event_queue.empty():
                event = event_queue.get()
                
                # Gestione uscita
                if event.content.lower() in ["esci", "quit", "spegniti"]:
                    logger.info("Ricevuto comando di spegnimento")
                    print("\nBuddy: Shutdown...")
                    if event.source == "jabra" and audio_enabled:
                        speak_text("Mi sto spegnendo.")
                    break

                # UI: Se l'input è vocale, lo stampiamo per confermare la comprensione
                # Usiamo \r per sovrascrivere il prompt "Tu > " che era in attesa
                if event.source == "jabra":
                    print(f"\rTu (🗣️) > {event.content}")
                
                # Se era tastiera, il "Tu >" è già stato riempito dall'input dell'utente, 
                # quindi non serve ristamparlo, ma logghiamo.
                logger.info(f"Input processato ({event.source}): {event.content}")

                # Processo Cognitivo
                db.add_history("user", event.content)
                risposta = buddy.respond(event.content)
                db.add_history("model", risposta)

                # Output
                print(f"Buddy > {risposta}")
                
                # Ripristina il prompt per il prossimo input
                print("\nTu > ", end="", flush=True)

                # Parla solo se l'audio è abilitato e l'input era vocale
                if event.source == "jabra" and audio_enabled:
                    speak_text(risposta)
                
                event_queue.task_done()

            # 2. GESTIONE ARCHIVISTA (Silenziosa)
            current_time = time.time()
            if current_time - last_archive_time > 30:
                unprocessed = db.get_unprocessed_history()
                if len(unprocessed) > 0:
                    logger.debug(f"Avvio archiviazione per {len(unprocessed)} messaggi")
                    archivist.distill_and_save(db)
                    logger.debug("Fine archiviazione")
                
                last_archive_time = current_time

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nBuddy: Arresto forzato.")
        logger.warning("Arresto forzato da tastiera")

if __name__ == "__main__":
    main()