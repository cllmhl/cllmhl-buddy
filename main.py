from logging.handlers import RotatingFileHandler
import os
import sys
import stat
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
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# --- CONFIGURAZIONE NAMED PIPE (FIFO) ---
PIPE_PATH = "/tmp/buddy_pipe"

def create_pipe():
    """Crea la Named Pipe se non esiste."""
    if os.path.exists(PIPE_PATH):
        # Rimuovi pipe esistente (potrebbe essere rimasta da una sessione precedente)
        try:
            os.unlink(PIPE_PATH)
        except Exception as e:
            logger.warning(f"Impossibile rimuovere pipe esistente: {e}")
    
    try:
        os.mkfifo(PIPE_PATH)
        # Permessi di lettura/scrittura per tutti (così puoi scrivere anche come altro user)
        os.chmod(PIPE_PATH, 0o666)
        logger.info(f"Named Pipe creata: {PIPE_PATH}")
    except Exception as e:
        logger.error(f"Errore creazione Named Pipe: {e}")
        raise

def keyboard_thread(event_queue):
    """Legge comandi dalla tastiera (stdin)."""
    logger.info("Thread tastiera avviato")
    print("Tu > ", end="", flush=True)
    
    while True:
        try:
            text = input()
            if text:
                event = BuddyEvent(source="terminal", content=text, timestamp=time.time())
                event_queue.put(event)
                print("Tu > ", end="", flush=True)
        except EOFError:
            logger.info("EOF ricevuto, thread tastiera termina")
            break
        except Exception as e:
            logger.error(f"Errore lettura tastiera: {e}")
            break

def pipe_thread(event_queue):
    """Legge comandi dalla Named Pipe."""
    logger.info(f"Thread Pipe avviato. In ascolto su {PIPE_PATH}")
    
    while True:
        try:
            # Apre la pipe in modalità lettura (blocca fino a quando qualcuno scrive)
            with open(PIPE_PATH, 'r') as pipe:
                for line in pipe:
                    text = line.strip()
                    if text:
                        logger.info(f"Comando ricevuto da pipe: {text}")
                        event = BuddyEvent(source="pipe", content=text, timestamp=time.time())
                        event_queue.put(event)
        except Exception as e:
            logger.error(f"Errore lettura pipe: {e}")
            time.sleep(1)  # Attendi prima di riprovare

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

    # Crea Named Pipe per input comandi
    create_pipe()
    
    # Avvio Threads Input
    # Rileva se c'è un terminale interattivo (stdin connesso)
    has_terminal = sys.stdin.isatty()
    
    if has_terminal:
        # Modalità interattiva: tastiera + pipe
        t_kbd = threading.Thread(target=keyboard_thread, args=(event_queue,), daemon=True, name="KbdThread")
        t_kbd.start()
        logger.info("Modalità INTERATTIVA: Tastiera + Pipe attivi")
    else:
        # Modalità servizio: solo pipe
        logger.info("Modalità SERVIZIO: Solo Pipe attiva")
    
    # Thread Pipe sempre attivo
    t_pipe = threading.Thread(target=pipe_thread, args=(event_queue,), daemon=True, name="PipeThread")
    t_pipe.start()
    
    ears.start() # Avvia il thread di ascolto (Jabra)

    print("\n--- Buddy OS Online (Refactored) ---")
    print(f"Audio Mode: STT={ears.mode.upper()} / TTS={voice.mode.upper()}")
    print(f"Wake Word: {'ATTIVO ✅' if ears.enabled else 'DISABILITATO ⚠️'}")
    
    if has_terminal:
        print(f"Input: TASTIERA + Pipe ({PIPE_PATH})")
        print("Scrivi direttamente o usa: ./buddy_cmd.sh 'messaggio'\n")
    else:
        print(f"Input: Pipe ({PIPE_PATH})")
        print("Comandi: echo 'messaggio' > /tmp/buddy_pipe\n")

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
                    print(f"\rTu (voce) > {event.content}")
                elif event.source == "pipe":
                    print(f"\rTu (pipe) > {event.content}")
                # Se source == "terminal" il prompt è già gestito da keyboard_thread
                
                logger.info(f"Input processato ({event.source}): {event.content}")

                # Processo Cognitivo
                # Nota: Non accendiamo più i LED manualmente qui, lo fa voice.speak() o ears.listen() internamente
                # Se volessimo un LED per il "pensiero", potremmo aggiungerlo a io_buddy o usare uno dei led esistenti.
                
                db.add_history("user", event.content)
                risposta = buddy.respond(event.content)
                db.add_history("model", risposta)

                # Output
                print(f"Buddy > {risposta}")

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