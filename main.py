from logging.handlers import RotatingFileHandler
import os
import logging
from dotenv import load_dotenv
import threading
import queue
import time
from dataclasses import dataclass # Mantenuto per compatibilità type checking se serve

# Le tue classi esistenti
from database_buddy import BuddyDatabase
from brain import BuddyBrain
from archivist import BuddyArchivist

# Nuova gestione IO separata
from io_buddy import BuddyEars, BuddyVoice, silence_alsa, BuddyEvent

# --- CONFIGURAZIONE LOGGING ---
handler = RotatingFileHandler('buddy_system.log', maxBytes=10*1024*1024, backupCount=1)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(threadName)s - %(message)s')
handler.setFormatter(formatter)

logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("chromadb").setLevel(logging.INFO)
logging.getLogger("posthog").setLevel(logging.ERROR)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

# --- THREAD TASTIERA (Mantenuto nel main perché è input di sistema standard) ---
def keyboard_thread(event_queue):
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

# --- MAIN ---
def main():
    # Silenzia ALSA (definito in io_buddy)
    silence_alsa()

    # Carica configurazione
    load_dotenv("config.env")
    load_dotenv(".env")
    
    api_key = os.getenv("GOOGLE_API_KEY")
    
    # Coda centrale eventi
    event_queue = queue.Queue()

    # Inizializzazione Sottosistemi
    try:
        db = BuddyDatabase()
        buddy = BuddyBrain(api_key)
        archivist = BuddyArchivist(api_key=api_key)
        
        # IO Systems
        voice = BuddyVoice() # Gestisce TTS e LED Verde
        # Ears ha bisogno della coda per inviare eventi e del flag 'speaking' della voce per non ascoltarsi
        ears = BuddyEars(event_queue, voice.is_speaking_event) # Gestisce Mic e LED Blu
        
        logger.info("Sottosistemi inizializzati correttamente")
    except Exception as e:
        print(f"Errore critico in avvio: {e}")
        return

    # Avvio Threads Input
    t_key = threading.Thread(target=keyboard_thread, args=(event_queue,), daemon=True, name="KbdThread")
    t_key.start()
    
    ears.start() # Avvia il thread di ascolto (Jabra)

    print("\n--- Buddy OS Online (Refactored) ---")
    print(f"Audio Mode: STT={ears.mode.upper()} / TTS={voice.mode.upper()}")
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
                    # Se l'input era vocale, saluta
                    if event.source == "jabra":
                        voice.speak("Mi sto spegnendo.")
                    break

                # UI Feedback
                if event.source == "jabra":
                    print(f"\rTu (🗣️) > {event.content}")
                logger.info(f"Input processato ({event.source}): {event.content}")

                # Processo Cognitivo
                # Nota: Non accendiamo più i LED manualmente qui, lo fa voice.speak() o ears.listen() internamente
                # Se volessimo un LED per il "pensiero", potremmo aggiungerlo a io_buddy o usare uno dei led esistenti.
                
                db.add_history("user", event.content)
                risposta = buddy.respond(event.content)
                db.add_history("model", risposta)

                # Output
                print(f"Buddy > {risposta}")
                print("\nTu > ", end="", flush=True)

                # Parla solo se l'input era vocale (o configurabile diversamente in futuro)
                if event.source == "jabra":
                    voice.speak(risposta)
                
                event_queue.task_done()

            # 2. GESTIONE ARCHIVISTA
            current_time = time.time()
            if current_time - last_archive_time > 30:
                unprocessed = db.get_unprocessed_history()
                if len(unprocessed) > 0:
                    logger.debug(f"Avvio archiviazione per {len(unprocessed)} messaggi")
                    archivist.distill_and_save(db)
                last_archive_time = current_time
            
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nBuddy: Arresto forzato.")
        logger.warning("Arresto forzato da tastiera")

if __name__ == "__main__":
    main()